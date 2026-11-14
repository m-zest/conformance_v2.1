"""Alert rules and evaluation.

Alerts are raised on new exposure only: a value that the same user already
sent (for example because a chat client resends the conversation history) does
not raise a second alert. Alerts for the same rule, user and tool on the same
day are grouped into one alert with an occurrence count.
"""
from __future__ import annotations

import hashlib
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .detection.model import SEVERITY, SEVERITY_NAMES, entity_label
from .models import Alert, AlertEvent, AlertRule, Finding, RequestLog

DEFAULT_ALERT_RULES = [
    {"id": "credential-exposure", "name": "Credential shared with an AI tool", "kind": "finding",
     "description": "A secret such as a cloud key, access token, private key or database password was sent.",
     "params": {"categories": ["secret.credential"], "min_severity": "high"}},
    {"id": "sensitive-personal-data", "name": "Sensitive personal data shared", "kind": "finding",
     "description": "Financial identifiers, national IDs or health information were sent.",
     "params": {"categories": ["pii.financial", "pii.identity", "pii.health"], "min_severity": "high"}},
    {"id": "confidential-business-data", "name": "Confidential business data shared", "kind": "finding",
     "description": "Content carrying a confidentiality marking or a protected term was sent.",
     "params": {"categories": ["confidential"], "min_severity": "medium"}},
    {"id": "prompt-injection", "name": "Prompt injection attempt", "kind": "finding",
     "description": "The request tried to override instructions or extract hidden configuration.",
     "params": {"categories": ["injection"], "min_severity": "medium"}},
    {"id": "unsafe-content", "name": "Unsafe content request", "kind": "finding",
     "description": "The guard model classified the request as unsafe.",
     "params": {"categories": ["content_safety"], "min_severity": "medium"}},
    {"id": "bulk-personal-data", "name": "Unusual volume of personal data from one user", "kind": "volume",
     "description": "One user sent many distinct personal data items in a short period.",
     "params": {"categories": ["pii.financial", "pii.identity", "pii.health", "pii.contact"],
                "window_minutes": 30, "threshold": 15}},
]


def _dedupe_key(rule_id: str, user_id: str | None, app_id: str | None, day: str) -> str:
    return hashlib.sha1(f"{rule_id}|{user_id}|{app_id}|{day}".encode()).hexdigest()


async def evaluate(session: AsyncSession, request: RequestLog, findings: list[Finding], *, user_label: str,
                   app_name: str, rules: list[AlertRule]) -> list[Alert]:
    """Create or update alerts for one stored request. Returns alerts that were newly created."""
    created: list[Alert] = []
    fresh = [f for f in findings if f.is_new]
    if not fresh:
        return created
    day = request.ts.strftime("%Y-%m-%d")
    for rule in rules:
        if not rule.enabled:
            continue
        params = rule.params or {}
        categories = set(params.get("categories") or [])
        sources = params.get("sources")
        if sources and request.source not in sources:
            continue
        matched = [f for f in fresh if f.category in categories]
        if not matched:
            continue
        if rule.kind == "volume":
            window = request.ts - timedelta(minutes=int(params.get("window_minutes", 30)))
            count = (await session.execute(
                select(func.count(Finding.id)).where(
                    Finding.user_id == request.user_id, Finding.is_new.is_(True), Finding.ts >= window,
                    Finding.ts <= request.ts, Finding.category.in_(categories)))).scalar_one()
            if count < int(params.get("threshold", 15)):
                continue
            severity = SEVERITY["high"]
            summary = (f"{user_label} sent {count} distinct personal data items within "
                       f"{params.get('window_minutes', 30)} minutes. Most recent tool: {app_name}.")
            key = _dedupe_key(rule.id, request.user_id, None, day)
        else:
            minimum = SEVERITY.get(params.get("min_severity", "medium"), 2)
            matched = [f for f in matched if f.severity >= minimum]
            if not matched:
                continue
            severity = max(f.severity for f in matched)
            outcome = {"blocked": "The request was blocked.", "masked": "The values were masked before forwarding.",
                       "observed": "Observed from vendor logs, no inline control."}.get(
                request.action, "The request was forwarded.")
            if request.would_action and request.action == "allowed":
                outcome = f"Policy is in monitor mode. In enforce mode this would be {request.would_action}ed."
            types = ", ".join(sorted({entity_label(f.entity_type) for f in matched}))
            verb = "attempted" if categories == {"injection"} else "sent"
            summary = f"{user_label} {verb} {types} {'in' if verb == 'attempted' else 'to'} {app_name}. {outcome}"
            key = _dedupe_key(rule.id, request.user_id, request.app_id, day)
        entity_types = sorted({f.entity_type for f in matched})
        existing = (await session.execute(
            select(Alert).where(Alert.dedupe_key == key, Alert.status.in_(("open", "acknowledged")))
        )).scalars().first()
        if existing:
            existing.occurrences += 1
            existing.last_seen_at = request.ts
            existing.last_request_id = request.id
            existing.severity = max(existing.severity, severity)
            merged = sorted(set(filter(None, existing.entity_types.split(","))) | set(entity_types))
            existing.entity_types = ",".join(merged)[:255]
            continue
        alert = Alert(created_at=request.ts, last_seen_at=request.ts, rule_id=rule.id, severity=severity,
                      title=rule.name, summary=summary, source=request.source, user_id=request.user_id,
                      app_id=request.app_id, request_id=request.id, last_request_id=request.id,
                      entity_types=",".join(entity_types)[:255], dedupe_key=key)
        session.add(alert)
        await session.flush()
        session.add(AlertEvent(alert_id=alert.id, ts=request.ts, actor="system", action="created",
                               note=f"Raised by rule: {rule.name}"))
        created.append(alert)
    return created


def alert_public(alert: Alert, user_label: str = "", app_name: str = "") -> dict:
    return {"id": alert.id, "title": alert.title, "summary": alert.summary,
            "severity": SEVERITY_NAMES.get(alert.severity, "medium"), "source": alert.source,
            "user": user_label, "tool": app_name, "created_at": alert.created_at.isoformat(),
            "rule": alert.rule_id}
