"""Read APIs behind the dashboard: overview, activity, alerts, users and teams."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import bucket_to_iso, get_session, time_bucket, utcnow
from ..detection.model import CATEGORIES, SEVERITY, SEVERITY_NAMES, entity_label
from ..models import Admin, Alert, AlertEvent, Application, Finding, LedgerEntry, RequestLog, User
from ..security import analyst_or_admin, any_role, audit
from .common import (RISK_WEIGHTS, alert_row, app_brief, finding_row, iso, name_maps, request_row, risk_score,
                     user_brief, window)

router = APIRouter(prefix="/api", tags=["insights"])
R = RequestLog


def _n(value) -> float:
    return value or 0


async def _totals(session: AsyncSession, start: datetime, end: datetime, *where) -> dict:
    row = (await session.execute(select(
        func.count(R.id), func.count(func.distinct(R.user_id)),
        func.sum(case((R.new_finding_count > 0, 1), else_=0)),
        func.sum(case((R.action == "blocked", 1), else_=0)),
        func.sum(case((R.action == "masked", 1), else_=0)),
        func.sum(case((R.would_action.is_not(None), 1), else_=0)),
        func.sum(R.cost_usd), func.sum(R.input_tokens + R.output_tokens),
        func.sum(case((R.source == "gateway", 1), else_=0)),
    ).where(R.ts >= start, R.ts < end, *where))).one()
    return {"requests": row[0], "active_users": row[1], "flagged": int(_n(row[2])), "blocked": int(_n(row[3])),
            "masked": int(_n(row[4])), "would_enforce": int(_n(row[5])), "cost_usd": round(_n(row[6]), 2),
            "tokens": int(_n(row[7])), "governed": int(_n(row[8]))}


async def _series(session: AsyncSession, start: datetime, end: datetime, unit: str, *where) -> list[dict]:
    bucket = time_bucket(R.ts, unit).label("bucket")
    rows = (await session.execute(select(
        bucket, func.count(R.id), func.sum(case((R.new_finding_count > 0, 1), else_=0)),
        func.sum(case((R.action == "blocked", 1), else_=0)), func.sum(case((R.action == "masked", 1), else_=0)),
    ).where(R.ts >= start, R.ts < end, *where).group_by(bucket).order_by(bucket))).all()
    found = {bucket_to_iso(b): (c, int(_n(f)), int(_n(bl)), int(_n(m))) for b, c, f, bl, m in rows}
    step = timedelta(hours=1) if unit == "hour" else timedelta(days=1)
    cursor = start.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    if unit == "day":
        cursor = cursor.replace(hour=0)
    out = []
    while cursor < end:
        key = cursor.strftime("%Y-%m-%dT%H:%M:%SZ")
        c, f, bl, m = found.get(key, (0, 0, 0, 0))
        out.append({"t": key, "requests": c, "flagged": f, "blocked": bl, "masked": m})
        cursor += step
    return out


async def _user_stats(session: AsyncSession, start: datetime, end: datetime, *where) -> dict[str, dict]:
    stats: dict[str, dict] = defaultdict(lambda: {"requests": 0, "flagged": 0, "blocked": 0, "masked": 0,
                                                 "points": 0, "findings": 0, "cost_usd": 0.0, "last": None})
    rows = (await session.execute(select(
        R.user_id, func.count(R.id), func.sum(case((R.new_finding_count > 0, 1), else_=0)),
        func.sum(case((R.action == "blocked", 1), else_=0)), func.sum(case((R.action == "masked", 1), else_=0)),
        func.sum(R.cost_usd), func.max(R.ts),
    ).where(R.ts >= start, R.ts < end, R.user_id.is_not(None), *where).group_by(R.user_id))).all()
    for uid, count, flagged, blocked, masked, cost, last in rows:
        stats[uid].update(requests=count, flagged=int(_n(flagged)), blocked=int(_n(blocked)),
                          masked=int(_n(masked)), cost_usd=round(_n(cost), 2), last=last)
    frows = (await session.execute(select(Finding.user_id, Finding.severity, func.count(Finding.id)).where(
        Finding.ts >= start, Finding.ts < end, Finding.is_new.is_(True), Finding.user_id.is_not(None)
    ).group_by(Finding.user_id, Finding.severity))).all()
    for uid, severity, count in frows:
        if uid in stats:
            stats[uid]["points"] += RISK_WEIGHTS.get(severity, 0) * count
            stats[uid]["findings"] += count
    for s in stats.values():
        s["risk"] = risk_score(s.pop("points"))
    return stats


def _delta(current: float, previous: float) -> float | None:
    if not previous:
        return None
    return round((current - previous) / previous * 100, 1)


@router.get("/overview")
async def overview(range: str = "7d", _: Admin = Depends(any_role), session: AsyncSession = Depends(get_session)):
    start, end, unit = window(range)
    prev_start = start - (end - start)
    now = await _totals(session, start, end)
    prev = await _totals(session, prev_start, start)
    users, apps = await name_maps(session)

    cat_rows = (await session.execute(select(Finding.category, func.count(Finding.id)).where(
        Finding.ts >= start, Finding.ts < end, Finding.is_new.is_(True)).group_by(Finding.category))).all()
    categories = sorted(({"category": c, "label": CATEGORIES.get(c, c), "count": n} for c, n in cat_rows),
                        key=lambda x: -x["count"])

    stats = await _user_stats(session, start, end)
    top_users = sorted(({"user": user_brief(users.get(uid)), **s, "last": iso(s["last"])}
                        for uid, s in stats.items() if users.get(uid) and s["risk"] > 0),
                       key=lambda x: (-x["risk"], -x["flagged"]))[:8]

    teams: dict[str, dict] = defaultdict(lambda: {"users": 0, "requests": 0, "flagged": 0, "blocked": 0,
                                                 "risk_sum": 0, "risk_max": 0})
    for uid, s in stats.items():
        user = users.get(uid)
        if user is None or user.source == "service":
            continue
        t = teams[user.team or "Unassigned"]
        t["users"] += 1
        t["requests"] += s["requests"]
        t["flagged"] += s["flagged"]
        t["blocked"] += s["blocked"]
        t["risk_sum"] += s["risk"]
        t["risk_max"] = max(t["risk_max"], s["risk"])
    team_rows = sorted(({"team": name, "users": t["users"], "requests": t["requests"], "flagged": t["flagged"],
                         "blocked": t["blocked"], "risk_avg": round(t["risk_sum"] / t["users"]),
                         "risk_max": t["risk_max"],
                         "flag_rate": round(t["flagged"] / t["requests"] * 100, 1) if t["requests"] else 0}
                        for name, t in teams.items()), key=lambda x: -x["flagged"])

    app_rows = (await session.execute(select(
        R.app_id, func.count(R.id), func.count(func.distinct(R.user_id)),
        func.sum(case((R.new_finding_count > 0, 1), else_=0)),
        func.sum(case((R.action == "blocked", 1), else_=0)), func.sum(case((R.action == "masked", 1), else_=0)),
        func.sum(R.cost_usd),
    ).where(R.ts >= start, R.ts < end).group_by(R.app_id))).all()
    by_app = sorted(({"app": app_brief(apps.get(aid)), "requests": c, "users": u, "flagged": int(_n(f)),
                      "blocked": int(_n(b)), "masked": int(_n(m)), "cost_usd": round(_n(cost), 2),
                      "flag_rate": round(_n(f) / c * 100, 1) if c else 0}
                     for aid, c, u, f, b, m, cost in app_rows if apps.get(aid)), key=lambda x: -x["requests"])

    sample = sorted((await session.execute(select(R.overhead_ms).where(
        R.source == "gateway", R.ts >= start, R.action != "error").order_by(R.ts.desc()).limit(5000))).scalars())
    latency = {"p50": round(sample[len(sample) // 2], 1), "p95": round(sample[int(len(sample) * 0.95)], 1),
               "samples": len(sample)} if sample else None

    week = await _totals(session, end - timedelta(days=7), end)
    open_alerts = (await session.execute(select(Alert.severity, func.count(Alert.id)).where(
        Alert.status == "open").group_by(Alert.severity))).all()
    recent = (await session.execute(select(Alert).where(Alert.status.in_(("open", "acknowledged")))
                                    .order_by(Alert.severity.desc(), Alert.created_at.desc()).limit(6))).scalars()
    return {
        "range": range, "start": iso(start), "end": iso(end), "unit": unit,
        "kpis": {**now, "flag_rate": round(now["flagged"] / now["requests"] * 100, 1) if now["requests"] else 0,
                 "open_alerts": sum(n for _, n in open_alerts),
                 "open_alerts_high": sum(n for s, n in open_alerts if s >= SEVERITY["high"])},
        "deltas": {k: _delta(now[k], prev[k]) for k in ("requests", "active_users", "flagged", "blocked", "masked",
                                                       "cost_usd")},
        "series": await _series(session, start, end, unit),
        "categories": categories, "top_users": top_users, "teams": team_rows, "by_app": by_app,
        "latency": latency,
        "cost_projection_30d": round(week["cost_usd"] / 7 * 30, 2),
        "coverage": {"governed": now["governed"], "observed": now["requests"] - now["governed"],
                     "governed_tools": sum(1 for a in apps.values() if a.kind == "gateway" and a.enabled),
                     "observed_tools": sum(1 for a in apps.values() if a.kind == "connector")},
        "recent_alerts": [alert_row(a, users, apps) for a in recent],
    }


@router.get("/activity")
async def activity(range: str = "7d", user_id: str | None = None, app_id: str | None = None,
                   action: str | None = None, category: str | None = None, source: str | None = None,
                   severity: str | None = None, flagged: bool = False, q: str | None = None,
                   cursor: str | None = None, limit: int = Query(50, le=200),
                   _: Admin = Depends(any_role), session: AsyncSession = Depends(get_session)):
    start, end, _unit = window(range)
    conditions = [R.ts >= start, R.ts < end]
    if user_id:
        conditions.append(R.user_id == user_id)
    if app_id:
        conditions.append(R.app_id == app_id)
    if action == "would_enforce":
        conditions.append(R.would_action.is_not(None))
    elif action:
        conditions.append(R.action == action)
    if category:
        conditions.append(R.categories.like(f"%{category}%"))
    if source:
        conditions.append(R.source == source)
    if severity in SEVERITY:
        conditions.append(R.severity >= SEVERITY[severity])
    if flagged:
        conditions.append(R.finding_count > 0)
    if q:
        like = f"%{q.strip().lower()}%"
        matching = select(User.id).where(or_(func.lower(User.display_name).like(like),
                                             func.lower(User.email).like(like), func.lower(User.team).like(like)))
        conditions.append(or_(R.user_id.in_(matching), R.id == q.strip(), func.lower(R.model).like(like)))
    total = (await session.execute(select(func.count(R.id)).where(*conditions))).scalar_one()
    if cursor:
        try:
            ts_raw, _, rid = cursor.partition("|")
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            conditions.append(or_(R.ts < ts, and_(R.ts == ts, R.id < rid)))
        except ValueError:
            raise HTTPException(400, "Invalid cursor")
    rows = (await session.execute(select(R).where(*conditions).order_by(R.ts.desc(), R.id.desc())
                                  .limit(limit + 1))).scalars().all()
    users, apps = await name_maps(session)
    page = rows[:limit]
    next_cursor = f"{iso(page[-1].ts)}|{page[-1].id}" if len(rows) > limit else None
    return {"total": total, "items": [request_row(r, users, apps) for r in page], "next_cursor": next_cursor}


@router.get("/activity/{request_id}")
async def activity_detail(request_id: str, _: Admin = Depends(any_role),
                          session: AsyncSession = Depends(get_session)):
    r = (await session.execute(select(R).where(R.id == request_id))).scalar_one_or_none()
    if r is None:
        raise HTTPException(404, "Request not found")
    users, apps = await name_maps(session)
    findings = (await session.execute(select(Finding).where(Finding.request_id == r.id)
                                      .order_by(Finding.severity.desc(), Finding.id))).scalars().all()
    entry = (await session.execute(select(LedgerEntry).where(
        LedgerEntry.record_type == "request", LedgerEntry.record_id == r.id))).scalars().first()
    related = (await session.execute(select(Alert).where(
        or_(Alert.request_id == r.id, Alert.last_request_id == r.id)))).scalars().all()
    return {
        **request_row(r, users, apps), "prompt_text": r.prompt_text, "response_text": r.response_text,
        "prompt_chars": r.prompt_chars, "prompt_sha256": r.prompt_sha256, "upstream_ms": r.upstream_ms,
        "upstream_status": r.upstream_status, "usage_estimated": r.usage_estimated, "error": r.error,
        "policy_id": r.policy_id, "policy_version": r.policy_version, "provider": r.provider,
        "compliance_token": bool(r.token_jti),
        "findings": [finding_row(f) for f in findings],
        "ledger": {"seq": entry.seq, "entry_hash": entry.entry_hash, "prev_hash": entry.prev_hash,
                   "signed": bool(entry.signature)} if entry else None,
        "alerts": [alert_row(a, users, apps) for a in related],
    }


@router.get("/alerts")
async def list_alerts(status: str = "open", severity: str | None = None, source: str | None = None,
                      user_id: str | None = None, limit: int = Query(100, le=500),
                      _: Admin = Depends(any_role), session: AsyncSession = Depends(get_session)):
    conditions = []
    if status == "active":
        conditions.append(Alert.status.in_(("open", "acknowledged")))
    elif status != "all":
        conditions.append(Alert.status == status)
    if severity in SEVERITY:
        conditions.append(Alert.severity >= SEVERITY[severity])
    if source:
        conditions.append(Alert.source == source)
    if user_id:
        conditions.append(Alert.user_id == user_id)
    rows = (await session.execute(select(Alert).where(*conditions)
                                  .order_by(Alert.last_seen_at.desc()).limit(limit))).scalars().all()
    counts = dict((await session.execute(select(Alert.status, func.count(Alert.id)).group_by(Alert.status))).all())
    users, apps = await name_maps(session)
    return {"items": [alert_row(a, users, apps) for a in rows], "counts": counts}


@router.get("/alerts/{alert_id}")
async def alert_detail(alert_id: str, _: Admin = Depends(any_role), session: AsyncSession = Depends(get_session)):
    alert = (await session.execute(select(Alert).where(Alert.id == alert_id))).scalar_one_or_none()
    if alert is None:
        raise HTTPException(404, "Alert not found")
    users, apps = await name_maps(session)
    events = (await session.execute(select(AlertEvent).where(AlertEvent.alert_id == alert.id)
                                    .order_by(AlertEvent.ts))).scalars().all()
    request = None
    target = alert.last_request_id or alert.request_id
    if target:
        r = (await session.execute(select(R).where(R.id == target))).scalar_one_or_none()
        if r is not None:
            findings = (await session.execute(select(Finding).where(Finding.request_id == r.id)
                                              .order_by(Finding.severity.desc()))).scalars().all()
            request = {**request_row(r, users, apps), "prompt_text": r.prompt_text,
                       "findings": [finding_row(f) for f in findings]}
    return {**alert_row(alert, users, apps), "request": request,
            "events": [{"ts": iso(e.ts), "actor": e.actor, "action": e.action, "note": e.note} for e in events]}


class AlertUpdate(BaseModel):
    status: str | None = None
    assignee: str | None = None
    note: str | None = None


@router.post("/alerts/{alert_id}")
async def update_alert(alert_id: str, body: AlertUpdate, actor: Admin = Depends(analyst_or_admin),
                       session: AsyncSession = Depends(get_session)):
    alert = (await session.execute(select(Alert).where(Alert.id == alert_id))).scalar_one_or_none()
    if alert is None:
        raise HTTPException(404, "Alert not found")
    note = (body.note or "").strip()
    if body.status and body.status != alert.status:
        if body.status not in ("open", "acknowledged", "resolved", "false_positive"):
            raise HTTPException(400, "Unknown status")
        alert.status = body.status
        session.add(AlertEvent(alert_id=alert.id, actor=actor.email, action=body.status, note=note))
        await audit(session, actor.email, "alert.status", alert.id, {"status": body.status})
        note = ""
    if body.assignee is not None and body.assignee != (alert.assignee or ""):
        alert.assignee = body.assignee or None
        session.add(AlertEvent(alert_id=alert.id, actor=actor.email, action="assigned",
                               note=body.assignee or "unassigned"))
    if note:
        session.add(AlertEvent(alert_id=alert.id, actor=actor.email, action="note", note=note))
    await session.commit()
    return await alert_detail(alert_id, actor, session)


@router.get("/users")
async def list_users(range: str = "7d", q: str | None = None, team: str | None = None,
                     _: Admin = Depends(any_role), session: AsyncSession = Depends(get_session)):
    start, end, _unit = window(range)
    stats = await _user_stats(session, start, end)
    users = (await session.execute(select(User))).scalars().all()
    needle = (q or "").strip().lower()
    items = []
    for u in users:
        if team and (u.team or "Unassigned") != team:
            continue
        if needle and needle not in " ".join(filter(None, [u.display_name, u.email, u.team, u.external_id])).lower():
            continue
        s = stats.get(u.id, {"requests": 0, "flagged": 0, "blocked": 0, "masked": 0, "risk": 0, "findings": 0,
                             "cost_usd": 0.0, "last": None})
        items.append({**user_brief(u), "title": u.title, "github_login": u.github_login, **s,
                      "last": iso(s["last"] or u.last_seen)})
    items.sort(key=lambda x: (-x["risk"], -x["requests"]))
    teams = sorted({u.team or "Unassigned" for u in users if u.source != "service"})
    return {"items": items, "teams": teams}


@router.get("/users/{user_id}")
async def user_detail(user_id: str, range: str = "14d", _: Admin = Depends(any_role),
                      session: AsyncSession = Depends(get_session)):
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(404, "User not found")
    start, end, unit = window(range)
    users, apps = await name_maps(session)
    stats = (await _user_stats(session, start, end, R.user_id == user_id)).get(user_id, {})
    cats = (await session.execute(select(Finding.category, Finding.entity_type, func.count(Finding.id)).where(
        Finding.user_id == user_id, Finding.ts >= start, Finding.is_new.is_(True)
    ).group_by(Finding.category, Finding.entity_type))).all()
    app_rows = (await session.execute(select(
        R.app_id, func.count(R.id), func.sum(case((R.new_finding_count > 0, 1), else_=0)), func.max(R.ts),
    ).where(R.user_id == user_id, R.ts >= start).group_by(R.app_id))).all()
    recent = (await session.execute(select(R).where(R.user_id == user_id, R.finding_count > 0, R.ts >= start)
                                    .order_by(R.ts.desc()).limit(12))).scalars().all()
    alerts = (await session.execute(select(Alert).where(Alert.user_id == user_id)
                                    .order_by(Alert.created_at.desc()).limit(10))).scalars().all()
    return {
        **user_brief(user), "title": user.title, "github_login": user.github_login, "source": user.source,
        "first_seen": iso(user.first_seen), "last_seen": iso(user.last_seen),
        "stats": {**stats, "last": iso(stats.get("last"))} if stats else None,
        "series": await _series(session, start, end, unit, R.user_id == user_id),
        "findings": sorted(({"category": c, "label": CATEGORIES.get(c, c), "entity_type": e, "entity_label": entity_label(e),
                             "count": n}
                            for c, e, n in cats), key=lambda x: -x["count"]),
        "apps": [{"app": app_brief(apps.get(aid)), "requests": c, "flagged": int(_n(f)), "last": iso(last)}
                 for aid, c, f, last in app_rows if apps.get(aid)],
        "recent": [request_row(r, users, apps) for r in recent],
        "alerts": [alert_row(a, users, apps) for a in alerts],
    }


@router.get("/meta")
async def meta(_: Admin = Depends(any_role), session: AsyncSession = Depends(get_session)):
    """Lookup values for filters."""
    apps = (await session.execute(select(Application).order_by(Application.name))).scalars().all()
    return {"apps": [app_brief(a) for a in apps],
            "categories": [{"id": k, "label": v} for k, v in CATEGORIES.items()],
            "severities": list(SEVERITY_NAMES.values()), "now": iso(utcnow())}
