"""Observed tools: connector status and Copilot oversight views."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..connectors.scheduler import scheduler
from ..db import get_session, utcnow
from ..detection.model import CATEGORIES
from ..gateway.identity import directory
from ..models import Admin, Connector, CopilotSeat, CopilotUsageDaily, Finding, RequestLog, User
from ..security import admin_only, any_role, audit
from .common import iso, name_maps, request_row, user_brief, window
from .insights import _series

router = APIRouter(prefix="/api", tags=["copilot"])
R = RequestLog


def _connector_public(c: Connector) -> dict:
    return {"id": c.id, "name": c.name, "mode": c.mode, "last_sync_at": iso(c.last_sync_at),
            "last_status": c.last_status, "last_error": c.last_error, "items_synced": c.items_synced}


@router.get("/connectors")
async def connectors(_: Admin = Depends(any_role), session: AsyncSession = Depends(get_session)):
    return [_connector_public(c) for c in (await session.execute(select(Connector).order_by(Connector.name))).scalars()]


@router.post("/connectors/{connector_id}/sync")
async def sync_connector(connector_id: str, background: BackgroundTasks, actor: Admin = Depends(admin_only),
                         session: AsyncSession = Depends(get_session)):
    if connector_id not in scheduler.connectors:
        raise HTTPException(404, "Connector not found")
    await audit(session, actor.email, "connector.sync", connector_id)
    await session.commit()
    background.add_task(scheduler.sync, connector_id)
    return {"ok": True}


@router.get("/copilot")
async def copilot(range: str = "14d", _: Admin = Depends(any_role), session: AsyncSession = Depends(get_session)):
    start, end, unit = window(range)
    users, apps = await name_maps(session)
    rows = {c.id: c for c in (await session.execute(select(Connector))).scalars()}

    # Microsoft 365 Copilot: content is available, so the detectors apply.
    m365_where = (R.source == "m365_copilot",)
    total, active, flagged = (await session.execute(select(
        func.count(R.id), func.count(func.distinct(R.user_id)),
        func.sum(case((R.new_finding_count > 0, 1), else_=0))).where(R.ts >= start, R.ts < end, *m365_where))).one()
    host_rows = (await session.execute(select(
        R.host_app, func.count(R.id), func.sum(case((R.new_finding_count > 0, 1), else_=0)),
        func.count(func.distinct(R.user_id))).where(R.ts >= start, R.ts < end, *m365_where)
        .group_by(R.host_app))).all()
    cat_rows = (await session.execute(select(Finding.category, func.count(Finding.id)).where(
        Finding.app_id == "m365-copilot", Finding.ts >= start, Finding.ts < end, Finding.is_new.is_(True))
        .group_by(Finding.category))).all()
    recent = (await session.execute(select(R).where(R.ts >= start, R.finding_count > 0, *m365_where)
                                    .order_by(R.ts.desc()).limit(10))).scalars().all()
    user_rows = (await session.execute(select(
        R.user_id, func.count(R.id), func.sum(case((R.new_finding_count > 0, 1), else_=0))).where(
        R.ts >= start, R.ts < end, *m365_where).group_by(R.user_id))).all()
    m365 = {
        "connector": _connector_public(rows["m365-copilot"]) if "m365-copilot" in rows else None,
        "interactions": total, "active_users": active, "flagged": int(flagged or 0),
        "flag_rate": round((flagged or 0) / total * 100, 1) if total else 0,
        "series": await _series(session, start, end, unit, *m365_where),
        "by_host": sorted(({"host": h or "Copilot", "interactions": c, "flagged": int(f or 0), "users": u}
                           for h, c, f, u in host_rows), key=lambda x: -x["interactions"]),
        "categories": sorted(({"category": c, "label": CATEGORIES.get(c, c), "count": n} for c, n in cat_rows),
                             key=lambda x: -x["count"]),
        "top_users": sorted(({"user": user_brief(users.get(uid)), "interactions": c, "flagged": int(f or 0)}
                             for uid, c, f in user_rows if users.get(uid) and f), key=lambda x: -x["flagged"])[:8],
        "recent": [request_row(r, users, apps) for r in recent],
    }

    # GitHub Copilot: usage only.
    seats = (await session.execute(select(CopilotSeat).where(CopilotSeat.connector_id == "github-copilot"))).scalars().all()
    now = utcnow()
    active_7 = sum(1 for s in seats if s.last_activity_at and s.last_activity_at >= now - timedelta(days=7))
    active_30 = sum(1 for s in seats if s.last_activity_at and s.last_activity_at >= now - timedelta(days=30))
    inactive = sorted((s for s in seats if not s.last_activity_at or s.last_activity_at < now - timedelta(days=30)),
                      key=lambda s: (s.last_activity_at is not None, s.last_activity_at or now))
    usage = (await session.execute(select(CopilotUsageDaily).where(
        CopilotUsageDaily.connector_id == "github-copilot", CopilotUsageDaily.day >= start.date(),
        CopilotUsageDaily.day <= end.date()))).scalars().all()
    by_day: dict = defaultdict(lambda: {"active_users": 0, "interactions": 0, "generations": 0, "acceptances": 0})
    per_user: dict = defaultdict(lambda: {"interactions": 0, "generations": 0, "acceptances": 0, "days": 0,
                                         "loc_accepted": 0, "agent": False, "ide": Counter(), "model": Counter()})
    ides, languages, models = Counter(), Counter(), Counter()
    chat_users, agent_users = set(), set()
    for u in usage:
        d = by_day[u.day.isoformat()]
        d["active_users"] += 1
        d["interactions"] += u.interactions
        d["generations"] += u.code_generations
        d["acceptances"] += u.code_acceptances
        p = per_user[u.login]
        p["interactions"] += u.interactions
        p["generations"] += u.code_generations
        p["acceptances"] += u.code_acceptances
        p["loc_accepted"] += u.loc_accepted
        p["days"] += 1
        p["agent"] = p["agent"] or u.used_agent
        p["user_id"] = u.user_id
        if u.top_ide:
            ides[u.top_ide] += 1
            p["ide"][u.top_ide] += 1
        if u.top_language:
            languages[u.top_language] += 1
        if u.top_model:
            models[u.top_model] += 1
            p["model"][u.top_model] += 1
        if u.used_chat:
            chat_users.add(u.login)
        if u.used_agent:
            agent_users.add(u.login)
    generations = sum(d["generations"] for d in by_day.values())
    acceptances = sum(d["acceptances"] for d in by_day.values())
    github = {
        "connector": _connector_public(rows["github-copilot"]) if "github-copilot" in rows else None,
        "seats": len(seats), "active_7d": active_7, "active_30d": active_30, "inactive_30d": len(inactive),
        "acceptance_rate": round(acceptances / generations * 100, 1) if generations else None,
        "chat_users": len(chat_users), "agent_users": len(agent_users),
        "series": [{"t": day, **vals} for day, vals in sorted(by_day.items())],
        "by_ide": [{"name": k, "count": v} for k, v in ides.most_common(6)],
        "by_language": [{"name": k, "count": v} for k, v in languages.most_common(8)],
        "by_model": [{"name": k, "count": v} for k, v in models.most_common(6)],
        "users": sorted(({"login": login, "user": user_brief(users.get(p.get("user_id"))),
                          "interactions": p["interactions"], "generations": p["generations"],
                          "acceptances": p["acceptances"], "active_days": p["days"], "agent": p["agent"],
                          "loc_accepted": p["loc_accepted"],
                          "ide": p["ide"].most_common(1)[0][0] if p["ide"] else "",
                          "model": p["model"].most_common(1)[0][0] if p["model"] else ""}
                         for login, p in per_user.items()), key=lambda x: -x["interactions"]),
        "inactive": [{"login": s.login, "user": user_brief(users.get(s.user_id)),
                      "last_activity_at": iso(s.last_activity_at), "assigned_at": iso(s.assigned_at)}
                     for s in inactive[:25]],
    }
    return {"range": range, "start": iso(start), "end": iso(end), "m365": m365, "github": github}


class DirectoryEntry(BaseModel):
    email: str
    name: str | None = None
    team: str | None = None
    title: str | None = None
    github_login: str | None = None


@router.post("/users/import")
async def import_users(entries: list[DirectoryEntry], actor: Admin = Depends(admin_only),
                       session: AsyncSession = Depends(get_session)):
    """Load or update directory attributes (team, title, GitHub login) for monitored users."""
    for e in entries:
        ref = await directory.ensure_user(e.email, email=e.email, name=e.name, team=e.team, title=e.title,
                                          source="import", github_login=e.github_login)
        if e.github_login or e.title:
            user = (await session.execute(select(User).where(User.id == ref.id))).scalar_one()
            user.github_login = e.github_login or user.github_login
            user.title = e.title or user.title
    await audit(session, actor.email, "directory.import", "", {"entries": len(entries)})
    await session.commit()
    return {"imported": len(entries)}
