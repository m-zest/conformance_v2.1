"""Helpers shared by the dashboard API routers."""
from __future__ import annotations

import math
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import utcnow
from ..detection.model import CATEGORIES, SEVERITY_NAMES, entity_label
from ..models import Alert, Application, Finding, RequestLog, User

RANGES = {"24h": timedelta(hours=24), "7d": timedelta(days=7), "14d": timedelta(days=14),
          "30d": timedelta(days=30), "90d": timedelta(days=90)}
RISK_WEIGHTS = {0: 0, 1: 1, 2: 4, 3: 10, 4: 25}


def window(range_key: str) -> tuple[datetime, datetime, str]:
    span = RANGES.get(range_key, RANGES["7d"])
    end = utcnow()
    return end - span, end, "hour" if span <= timedelta(hours=48) else "day"


def risk_score(points: float) -> int:
    """Saturating 0 to 100 score from severity-weighted new findings."""
    return int(round(100 * (1 - math.exp(-points / 60)))) if points > 0 else 0


def iso(value: datetime | None) -> str | None:
    return value.isoformat().replace("+00:00", "Z") if value else None


async def name_maps(session: AsyncSession) -> tuple[dict, dict]:
    users = {u.id: u for u in (await session.execute(select(User))).scalars()}
    apps = {a.id: a for a in (await session.execute(select(Application))).scalars()}
    return users, apps


def user_brief(user: User | None) -> dict | None:
    if user is None:
        return None
    return {"id": user.id, "name": user.display_name or user.email or user.external_id, "email": user.email,
            "team": user.team, "unattributed": user.source == "service"}


def app_brief(app: Application | None) -> dict | None:
    if app is None:
        return None
    return {"id": app.id, "name": app.name, "kind": app.kind, "vendor": app.vendor}


def request_row(r: RequestLog, users: dict, apps: dict) -> dict:
    return {
        "id": r.id, "ts": iso(r.ts), "source": r.source, "user": user_brief(users.get(r.user_id)),
        "app": app_brief(apps.get(r.app_id)), "model": r.model, "host_app": r.host_app, "action": r.action,
        "would_action": r.would_action, "mode": r.mode, "severity": SEVERITY_NAMES.get(r.severity, "info"),
        "finding_count": r.finding_count, "new_finding_count": r.new_finding_count,
        "categories": [c for c in r.categories.split(",") if c], "input_tokens": r.input_tokens,
        "output_tokens": r.output_tokens, "cost_usd": r.cost_usd, "latency_ms": r.latency_ms,
        "overhead_ms": r.overhead_ms, "stream": r.stream, "protocol": r.protocol,
    }


def finding_row(f: Finding) -> dict:
    return {"id": f.id, "direction": f.direction, "detector": f.detector, "category": f.category,
            "category_label": CATEGORIES.get(f.category, f.category), "entity_type": f.entity_type, "entity_label": entity_label(f.entity_type),
            "severity": SEVERITY_NAMES.get(f.severity, "info"), "confidence": f.confidence, "action": f.action,
            "preview": f.preview, "is_new": f.is_new}


def alert_row(a: Alert, users: dict, apps: dict) -> dict:
    return {"id": a.id, "created_at": iso(a.created_at), "last_seen_at": iso(a.last_seen_at), "rule_id": a.rule_id,
            "severity": SEVERITY_NAMES.get(a.severity, "medium"), "title": a.title, "summary": a.summary,
            "source": a.source, "user": user_brief(users.get(a.user_id)), "app": app_brief(apps.get(a.app_id)),
            "request_id": a.request_id, "last_request_id": a.last_request_id, "occurrences": a.occurrences,
            "entity_types": [entity_label(e) for e in a.entity_types.split(",") if e], "status": a.status,
            "assignee": a.assignee}
