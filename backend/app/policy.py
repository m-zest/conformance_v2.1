"""Policy evaluation: maps findings to an action and decides what happens to the request."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from sqlalchemy import select

from .db import SessionLocal
from .detection.model import ACTION_RANK, CATEGORIES, MASKABLE, Finding
from .models import Application, Policy

DEFAULT_RULES = {
    "secret.credential": "block",
    "pii.financial": "mask",
    "pii.identity": "mask",
    "pii.health": "mask",
    "pii.contact": "log",
    "pii.person": "log",
    "confidential": "log",
    "injection": "log",
    "content_safety": "log",
}
STRICT_RULES = {**DEFAULT_RULES, "pii.contact": "mask", "confidential": "block", "injection": "block",
                "content_safety": "block"}


@dataclass
class PolicyView:
    id: str
    name: str
    mode: str
    rules: dict
    custom_terms: list
    version: int


@dataclass
class Decision:
    would: str = "allow"       # what the rules call for: allow | mask | block
    enforced: str = "allow"    # what is applied after the policy mode is taken into account
    severity: int = 0
    reasons: list[str] = field(default_factory=list)


def normalize_rules(rules: dict | None) -> dict:
    out = dict(DEFAULT_RULES)
    for category, action in (rules or {}).items():
        if category in CATEGORIES and action in ACTION_RANK:
            out[category] = "log" if action == "mask" and category not in MASKABLE else action
    return out


def apply_policy(policy: PolicyView, findings: list[Finding]) -> tuple[list[Finding], Decision]:
    kept: list[Finding] = []
    decision = Decision()
    rank = 0
    for f in findings:
        action = policy.rules.get(f.category, "log")
        if action == "allow":
            continue
        if action == "mask" and f.category not in MASKABLE:
            action = "log"
        f.action = action
        kept.append(f)
        decision.severity = max(decision.severity, f.severity)
        if ACTION_RANK[action] > rank:
            rank = ACTION_RANK[action]
        if action == "block" and f.entity_type not in decision.reasons:
            decision.reasons.append(f.entity_type)
    decision.would = {0: "allow", 1: "allow", 2: "mask", 3: "block"}[rank]
    decision.enforced = decision.would if policy.mode == "enforce" else "allow"
    return kept, decision


class PolicyStore:
    """Small TTL cache so the proxy path does not query the database on every request."""

    def __init__(self, ttl: float = 10.0) -> None:
        self.ttl = ttl
        self._by_app: dict[str, tuple[float, PolicyView]] = {}

    def invalidate(self) -> None:
        self._by_app.clear()

    async def for_app(self, app_id: str | None) -> PolicyView:
        key = app_id or "_default"
        hit = self._by_app.get(key)
        now = time.monotonic()
        if hit and now - hit[0] < self.ttl:
            return hit[1]
        async with SessionLocal() as session:
            policy = None
            if app_id:
                policy = (await session.execute(
                    select(Policy).join(Application, Application.policy_id == Policy.id)
                    .where(Application.id == app_id))).scalar_one_or_none()
            if policy is None:
                policy = (await session.execute(select(Policy).where(Policy.is_default.is_(True)))).scalars().first()
        view = to_view(policy)
        self._by_app[key] = (now, view)
        return view


def to_view(policy: Policy | None) -> PolicyView:
    if policy is None:
        return PolicyView("builtin", "Built-in default", "monitor", dict(DEFAULT_RULES), [], 1)
    return PolicyView(policy.id, policy.name, policy.mode, normalize_rules(policy.rules), policy.custom_terms or [],
                      policy.version)


policies = PolicyStore()
