"""Management APIs: tools and keys, policies, audit ledger, system settings."""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import ledger, notifications
from ..config import VERSION, settings
from ..db import get_session, utcnow
from ..detection.engine import DETECTOR_SET_VERSION, Redactor, engine, finalize_findings
from ..detection.model import ACTION_RANK, CATEGORIES, MASKABLE, SEVERITY, SEVERITY_NAMES, entity_label
from ..gateway.identity import directory
from ..models import (Admin, AlertRule, ApiKey, Application, AuditLog, LedgerEntry, Notification, Policy,
                      RequestLog, Setting, User, new_id)
from ..policy import apply_policy, normalize_rules, policies, to_view
from ..recorder import recorder
from ..security import admin_only, any_role, audit, generate_gateway_key, hash_key
from ..signing import signer
from .common import iso, window

router = APIRouter(prefix="/api", tags=["admin"])
R = RequestLog


# ---------------------------------------------------------------- tools and keys

class AppBody(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9][a-z0-9-]*$")
    description: str = ""
    owner: str = ""
    policy_id: str | None = None
    trust_end_user: bool = True


class AppPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    owner: str | None = None
    policy_id: str | None = None
    trust_end_user: bool | None = None
    enabled: bool | None = None


class KeyBody(BaseModel):
    name: str = ""
    user_email: str | None = None
    expires_days: int | None = Field(default=None, ge=1, le=3650)


def _app_public(a: Application, stats: dict | None = None, policy: Policy | None = None, keys: int = 0) -> dict:
    return {"id": a.id, "slug": a.slug, "name": a.name, "kind": a.kind, "vendor": a.vendor,
            "description": a.description, "owner": a.owner, "policy_id": a.policy_id,
            "policy_name": policy.name if policy else None, "policy_mode": policy.mode if policy else None,
            "trust_end_user": a.trust_end_user, "enabled": a.enabled, "created_at": iso(a.created_at),
            "active_keys": keys, **(stats or {"requests": 0, "users": 0, "flagged": 0, "blocked": 0, "masked": 0,
                                              "cost_usd": 0.0, "last": None})}


@router.get("/apps")
async def list_apps(range: str = "7d", _: Admin = Depends(any_role), session: AsyncSession = Depends(get_session)):
    start, end, _unit = window(range)
    apps = (await session.execute(select(Application).order_by(Application.kind.desc(), Application.name))).scalars().all()
    pols = {p.id: p for p in (await session.execute(select(Policy))).scalars()}
    default = next((p for p in pols.values() if p.is_default), None)
    rows = (await session.execute(select(
        R.app_id, func.count(R.id), func.count(func.distinct(R.user_id)),
        func.sum(case((R.new_finding_count > 0, 1), else_=0)), func.sum(case((R.action == "blocked", 1), else_=0)),
        func.sum(case((R.action == "masked", 1), else_=0)), func.sum(R.cost_usd), func.max(R.ts),
    ).where(R.ts >= start, R.ts < end).group_by(R.app_id))).all()
    stats = {aid: {"requests": c, "users": u, "flagged": int(f or 0), "blocked": int(b or 0), "masked": int(m or 0),
                   "cost_usd": round(cost or 0, 2), "last": iso(last)} for aid, c, u, f, b, m, cost, last in rows}
    keys = dict((await session.execute(select(ApiKey.app_id, func.count(ApiKey.id)).where(
        ApiKey.revoked_at.is_(None)).group_by(ApiKey.app_id))).all())
    week = dict((await session.execute(select(R.app_id, func.sum(R.cost_usd)).where(
        R.ts >= end - timedelta(days=7)).group_by(R.app_id))).all())
    out = []
    for a in apps:
        policy = pols.get(a.policy_id) or (default if a.kind == "gateway" else None)
        item = _app_public(a, stats.get(a.id), policy, keys.get(a.id, 0))
        item["cost_projection_30d"] = round((week.get(a.id) or 0) / 7 * 30, 2)
        out.append(item)
    return out


@router.post("/apps")
async def create_app(body: AppBody, actor: Admin = Depends(admin_only), session: AsyncSession = Depends(get_session)):
    if (await session.execute(select(Application).where(Application.slug == body.slug))).first():
        raise HTTPException(409, "A tool with this identifier already exists")
    app = Application(slug=body.slug, name=body.name, description=body.description, owner=body.owner,
                      policy_id=body.policy_id, trust_end_user=body.trust_end_user)
    session.add(app)
    await audit(session, actor.email, "tool.created", body.slug)
    await session.commit()
    return _app_public(app)


@router.patch("/apps/{app_id}")
async def update_app(app_id: str, body: AppPatch, actor: Admin = Depends(admin_only),
                     session: AsyncSession = Depends(get_session)):
    app = (await session.execute(select(Application).where(Application.id == app_id))).scalar_one_or_none()
    if app is None:
        raise HTTPException(404, "Tool not found")
    changes = body.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(app, key, value)
    await audit(session, actor.email, "tool.updated", app.slug, changes)
    await session.commit()
    directory.invalidate()
    policies.invalidate()
    return _app_public(app)


def _key_public(k: ApiKey, users: dict) -> dict:
    user = users.get(k.user_id)
    return {"id": k.id, "name": k.name, "prefix": k.prefix, "created_at": iso(k.created_at),
            "created_by": k.created_by, "last_used_at": iso(k.last_used_at), "expires_at": iso(k.expires_at),
            "revoked_at": iso(k.revoked_at), "user": (user.display_name or user.email) if user else None}


@router.get("/apps/{app_id}/keys")
async def list_keys(app_id: str, _: Admin = Depends(admin_only), session: AsyncSession = Depends(get_session)):
    keys = (await session.execute(select(ApiKey).where(ApiKey.app_id == app_id)
                                  .order_by(ApiKey.created_at.desc()))).scalars().all()
    users = {u.id: u for u in (await session.execute(select(User).where(
        User.id.in_([k.user_id for k in keys if k.user_id])))).scalars()} if keys else {}
    return [_key_public(k, users) for k in keys]


@router.post("/apps/{app_id}/keys")
async def create_key(app_id: str, body: KeyBody, actor: Admin = Depends(admin_only),
                     session: AsyncSession = Depends(get_session)):
    app = (await session.execute(select(Application).where(Application.id == app_id))).scalar_one_or_none()
    if app is None or app.kind != "gateway":
        raise HTTPException(404, "Tool not found")
    user_id = None
    if body.user_email:
        ref = await directory.ensure_user(body.user_email, email=body.user_email, source="key")
        user_id = ref.id
    raw = generate_gateway_key()
    key = ApiKey(id=new_id(), app_id=app.id, user_id=user_id, name=body.name or ("Personal key" if user_id else "Application key"),
                 prefix=raw[:10], key_hash=hash_key(raw), created_by=actor.email,
                 expires_at=utcnow() + timedelta(days=body.expires_days) if body.expires_days else None)
    session.add(key)
    await audit(session, actor.email, "key.created", app.slug, {"key_id": key.id, "personal": bool(user_id)})
    await session.commit()
    return {**_key_public(key, {}), "key": raw}


@router.delete("/keys/{key_id}")
async def revoke_key(key_id: str, actor: Admin = Depends(admin_only), session: AsyncSession = Depends(get_session)):
    key = (await session.execute(select(ApiKey).where(ApiKey.id == key_id))).scalar_one_or_none()
    if key is None:
        raise HTTPException(404, "Key not found")
    key.revoked_at = utcnow()
    await audit(session, actor.email, "key.revoked", key.prefix, {"key_id": key.id})
    await session.commit()
    directory.invalidate()
    return {"ok": True}


# ---------------------------------------------------------------- policies

class PolicyBody(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = ""
    mode: str = "monitor"
    rules: dict[str, str] = {}
    custom_terms: list[dict] = []


class PolicyTest(BaseModel):
    text: str = Field(max_length=50_000)
    policy_id: str | None = None


def _policy_public(p: Policy, usage: dict) -> dict:
    return {"id": p.id, "name": p.name, "description": p.description, "mode": p.mode,
            "rules": normalize_rules(p.rules), "custom_terms": p.custom_terms or [], "version": p.version,
            "is_default": p.is_default, "updated_at": iso(p.updated_at), "updated_by": p.updated_by,
            "tools": usage.get(p.id, [])}


def _validate_policy(body: PolicyBody) -> None:
    if body.mode not in ("monitor", "enforce"):
        raise HTTPException(400, "Mode must be monitor or enforce")
    for category, action in body.rules.items():
        if category not in CATEGORIES or action not in ACTION_RANK:
            raise HTTPException(400, f"Invalid rule for {category}")
    for term in body.custom_terms:
        if not (term.get("pattern") or "").strip():
            raise HTTPException(400, "Custom terms need a pattern")
        if term.get("type") == "regex":
            import re
            try:
                re.compile(term["pattern"])
            except re.error as exc:
                raise HTTPException(400, f"Invalid regular expression: {exc}")


async def _policy_usage(session: AsyncSession) -> dict:
    usage: dict[str, list] = {}
    for a in (await session.execute(select(Application).where(Application.kind == "gateway"))).scalars():
        if a.policy_id:
            usage.setdefault(a.policy_id, []).append(a.name)
    return usage


@router.get("/policies")
async def list_policies(_: Admin = Depends(any_role), session: AsyncSession = Depends(get_session)):
    usage = await _policy_usage(session)
    rows = (await session.execute(select(Policy).order_by(Policy.is_default.desc(), Policy.name))).scalars().all()
    return {"items": [_policy_public(p, usage) for p in rows],
            "categories": [{"id": k, "label": v, "maskable": k in MASKABLE} for k, v in CATEGORIES.items()]}


@router.post("/policies")
async def create_policy(body: PolicyBody, actor: Admin = Depends(admin_only),
                        session: AsyncSession = Depends(get_session)):
    _validate_policy(body)
    if (await session.execute(select(Policy).where(Policy.name == body.name))).first():
        raise HTTPException(409, "A policy with this name already exists")
    policy = Policy(name=body.name, description=body.description, mode=body.mode, rules=normalize_rules(body.rules),
                    custom_terms=body.custom_terms, updated_by=actor.email)
    session.add(policy)
    await audit(session, actor.email, "policy.created", body.name, {"mode": body.mode})
    await session.commit()
    return _policy_public(policy, {})


@router.put("/policies/{policy_id}")
async def update_policy(policy_id: str, body: PolicyBody, actor: Admin = Depends(admin_only),
                        session: AsyncSession = Depends(get_session)):
    _validate_policy(body)
    policy = (await session.execute(select(Policy).where(Policy.id == policy_id))).scalar_one_or_none()
    if policy is None:
        raise HTTPException(404, "Policy not found")
    before = {"mode": policy.mode, "rules": normalize_rules(policy.rules)}
    policy.name, policy.description, policy.mode = body.name, body.description, body.mode
    policy.rules = normalize_rules(body.rules)
    policy.custom_terms = body.custom_terms
    policy.version += 1
    policy.updated_at, policy.updated_by = utcnow(), actor.email
    changed = {k: v for k, v in policy.rules.items() if before["rules"].get(k) != v}
    await audit(session, actor.email, "policy.updated", policy.name,
                {"version": policy.version, "mode": {"from": before["mode"], "to": policy.mode}, "rules": changed})
    await session.commit()
    policies.invalidate()
    return _policy_public(policy, await _policy_usage(session))


@router.post("/policies/test")
async def test_policy(body: PolicyTest, _: Admin = Depends(any_role), session: AsyncSession = Depends(get_session)):
    """Dry run: what would the detectors and a policy do with this text. Nothing is stored."""
    policy = None
    if body.policy_id:
        policy = (await session.execute(select(Policy).where(Policy.id == body.policy_id))).scalar_one_or_none()
    if policy is None:
        policy = (await session.execute(select(Policy).where(Policy.is_default.is_(True)))).scalars().first()
    view = to_view(policy)
    detected = engine.scan_text(body.text, view.custom_terms)
    if engine.guard.enabled:
        detected += await engine.guard.classify(body.text)
    findings, decision = apply_policy(view, detected)
    finalize_findings(findings)
    return {
        "policy": view.name, "mode": view.mode, "would": decision.would, "enforced": decision.enforced,
        "redacted": Redactor().apply(body.text, findings),
        "forwarded": Redactor().apply(body.text, [f for f in findings if f.action == "mask"])
        if decision.enforced == "mask" else (None if decision.enforced == "block" else body.text),
        "findings": [{"category": f.category, "category_label": CATEGORIES.get(f.category, f.category),
                      "entity_type": f.entity_type, "entity_label": entity_label(f.entity_type),
                      "detector": f.detector, "confidence": f.confidence,
                      "severity": SEVERITY_NAMES.get(f.severity, "info"), "action": f.action, "start": f.start,
                      "end": f.end, "preview": f.preview} for f in findings],
    }


# ---------------------------------------------------------------- audit

@router.get("/audit/ledger")
async def ledger_entries(limit: int = Query(50, le=500), _: Admin = Depends(any_role),
                         session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(LedgerEntry).order_by(LedgerEntry.seq.desc()).limit(limit))).scalars().all()
    total = (await session.execute(select(func.count(LedgerEntry.seq)))).scalar_one()
    return {"total": total, "key_id": signer.kid, "items": [
        {"seq": e.seq, "ts": iso(e.ts), "record_type": e.record_type, "record_id": e.record_id,
         "entry_hash": e.entry_hash, "prev_hash": e.prev_hash, "signed": bool(e.signature)} for e in rows]}


@router.get("/audit/verify")
async def verify_ledger(actor: Admin = Depends(any_role), session: AsyncSession = Depends(get_session)):
    result = await ledger.verify(session)
    result["verified_at"] = iso(utcnow())
    return result


@router.get("/audit/admin-log")
async def admin_log(limit: int = Query(100, le=500), _: Admin = Depends(any_role),
                    session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(AuditLog).order_by(AuditLog.ts.desc()).limit(limit))).scalars().all()
    return [{"id": a.id, "ts": iso(a.ts), "actor": a.actor, "action": a.action, "target": a.target,
             "details": a.details} for a in rows]


@router.get("/audit/export")
async def export_records(start: datetime, end: datetime, format: str = "csv",
                         actor: Admin = Depends(any_role), session: AsyncSession = Depends(get_session)):
    """Export interaction records with their ledger hashes for an audit or regulator request."""
    if end - start > timedelta(days=366):
        raise HTTPException(400, "Export at most one year at a time")
    users = {u.id: u for u in (await session.execute(select(User))).scalars()}
    apps = {a.id: a for a in (await session.execute(select(Application))).scalars()}
    rows = (await session.execute(
        select(R, LedgerEntry).outerjoin(LedgerEntry, (LedgerEntry.record_id == R.id) & (
            LedgerEntry.record_type == "request")).where(R.ts >= start, R.ts < end).order_by(R.ts))).all()
    await audit(session, actor.email, "audit.export", f"{iso(start)} to {iso(end)}",
                {"records": len(rows), "format": format})
    await session.commit()
    fields = ["id", "timestamp", "source", "user", "team", "tool", "model", "policy_mode", "action", "would_action",
              "severity", "findings", "categories", "input_tokens", "output_tokens", "prompt_sha256",
              "ledger_seq", "ledger_hash"]

    def record(r: RequestLog, e: LedgerEntry | None) -> dict:
        user, app = users.get(r.user_id), apps.get(r.app_id)
        return {"id": r.id, "timestamp": iso(r.ts), "source": r.source,
                "user": (user.email or user.external_id) if user else "", "team": user.team if user else "",
                "tool": app.name if app else "", "model": r.model, "policy_mode": r.mode, "action": r.action,
                "would_action": r.would_action or "", "severity": SEVERITY_NAMES.get(r.severity, "info"),
                "findings": r.finding_count, "categories": r.categories, "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens, "prompt_sha256": r.prompt_sha256,
                "ledger_seq": e.seq if e else "", "ledger_hash": e.entry_hash if e else ""}

    stamp = utcnow().strftime("%Y%m%d-%H%M")
    if format == "json":
        payload = json.dumps({"exported_at": iso(utcnow()), "exported_by": actor.email, "signing_key_id": signer.kid,
                              "records": [record(r, e) for r, e in rows]}, indent=1)
        return StreamingResponse(iter([payload]), media_type="application/json", headers={
            "content-disposition": f'attachment; filename="conformance-audit-{stamp}.json"'})
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    for r, e in rows:
        writer.writerow(record(r, e))
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers={
        "content-disposition": f'attachment; filename="conformance-audit-{stamp}.csv"'})


# ---------------------------------------------------------------- settings

class RulePatch(BaseModel):
    enabled: bool | None = None
    params: dict | None = None


@router.get("/alert-rules")
async def alert_rules(_: Admin = Depends(any_role), session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(AlertRule).order_by(AlertRule.position))).scalars().all()
    return [{"id": r.id, "name": r.name, "description": r.description, "kind": r.kind, "params": r.params,
             "enabled": r.enabled} for r in rows]


@router.patch("/alert-rules/{rule_id}")
async def update_alert_rule(rule_id: str, body: RulePatch, actor: Admin = Depends(admin_only),
                            session: AsyncSession = Depends(get_session)):
    rule = (await session.execute(select(AlertRule).where(AlertRule.id == rule_id))).scalar_one_or_none()
    if rule is None:
        raise HTTPException(404, "Rule not found")
    if body.enabled is not None:
        rule.enabled = body.enabled
    if body.params is not None:
        merged = dict(rule.params or {})
        for key in ("min_severity", "threshold", "window_minutes"):
            if key in body.params:
                merged[key] = body.params[key]
        if merged.get("min_severity", "medium") not in SEVERITY:
            raise HTTPException(400, "Unknown severity")
        rule.params = merged
    await audit(session, actor.email, "alert_rule.updated", rule.id, body.model_dump(exclude_unset=True))
    await session.commit()
    recorder.invalidate_rules()
    return {"ok": True}


@router.get("/settings/system")
async def system_settings(_: Admin = Depends(any_role), session: AsyncSession = Depends(get_session)):
    demo = (await session.execute(select(Setting).where(Setting.key == "demo_data"))).scalar_one_or_none()
    recent = (await session.execute(select(Notification).order_by(Notification.ts.desc()).limit(20))).scalars().all()
    return {
        "version": VERSION, "detector_set": DETECTOR_SET_VERSION, "detectors": engine.status(),
        "scan_cache": {"hits": engine.cache_hits, "misses": engine.cache_misses},
        "recorder": {"dropped": recorder.dropped, "failed": recorder.failed},
        "privacy": {"store_prompts": settings.store_prompts, "store_responses": settings.store_responses,
                    "store_previews": settings.store_previews, "retention_days": settings.retention_days},
        "signing": {"enabled": settings.signing_enabled, "algorithm": "ES256", "key_id": signer.kid,
                    "issuer": settings.signing_issuer, "audience": settings.signing_audience,
                    "ttl_seconds": settings.signing_ttl},
        "identity": {"oidc_enabled": bool(settings.oidc_issuer), "oidc_issuer": settings.oidc_issuer},
        "upstreams": {"openai": settings.openai_base_url, "anthropic": settings.anthropic_base_url},
        "notifications": {"channels": notifications.channels(), "min_severity": settings.notify_min_severity,
                          "recent": [{"ts": iso(n.ts), "channel": n.channel, "subject": n.subject,
                                      "status": n.status, "detail": n.detail} for n in recent]},
        "demo": {"mode": settings.demo_mode, "data": demo.value if demo else None},
    }


@router.post("/settings/notifications/test")
async def test_notification(actor: Admin = Depends(admin_only)):
    if not any(c["configured"] for c in notifications.channels()):
        raise HTTPException(400, "No notification channel is configured")
    results = await notifications.send({
        "id": "test-" + new_id()[:8], "title": "Test notification", "severity": "high", "source": "gateway",
        "summary": f"Test sent from the dashboard by {actor.email}. No action is needed.",
        "user": "Test user", "tool": "Conformance", "created_at": iso(utcnow()), "rule": "test"})
    return {"results": results}
