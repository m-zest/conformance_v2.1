"""Demo data seeder.

Generates two weeks of synthetic gateway traffic for the fictional Meridian
Group roster. Prompts are synthetic, but every record is produced by the real
pipeline: the same detectors, policy evaluation, ledger and alert rules that
handle live traffic. Only the upstream call is skipped and the timestamps are
backdated. A flag is stored so the dashboard can label the data as demo data.

Run automatically on first start when DEMO_SEED=true, or by hand:

    python -m app.demo.seed --days 14
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import logging
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from demo import corpus, synth

from ..bootstrap import run as bootstrap
from ..config import settings
from ..db import SessionLocal, init_models, utcnow
from ..detection.engine import Redactor, Segment, engine
from ..gateway.identity import directory
from ..models import Alert, AlertEvent, Application, Policy, RequestLog, Setting
from ..policy import apply_policy, to_view
from ..recorder import Record, recorder

log = logging.getLogger("conformance.demo")

TEAM_APPS = {
    "Finance": [("internal-assistant", 9), ("contract-review", 1)],
    "Engineering": [("developer-tools", 7), ("internal-assistant", 3)],
    "Human Resources": [("internal-assistant", 10)],
    "Sales": [("internal-assistant", 8), ("contract-review", 2)],
    "Legal": [("contract-review", 6), ("internal-assistant", 4)],
    "Customer Support": [("support-desk", 8), ("internal-assistant", 2)],
    "Marketing": [("internal-assistant", 10)],
    "Data and Analytics": [("developer-tools", 5), ("internal-assistant", 5)],
}
APP_MODELS = {
    "internal-assistant": [("gpt-4o-mini", 7), ("gpt-4o", 3)],
    "support-desk": [("gpt-4o-mini", 10)],
    "contract-review": [("claude-sonnet-4-5", 10)],
    "developer-tools": [("claude-sonnet-4-5", 7), ("gpt-4.1", 3)],
}
PROTOCOLS = {"gpt": ("openai.chat", "openai"), "claude": ("anthropic.messages", "anthropic")}
# A few people behave riskily so that the rankings and alerts have something to show.
RISK_PROFILE = {"Tomasz Nowak": 0.16, "Marco Bianchi": 0.12, "Zofia Kowalska": 0.14, "Samuel Adeyemi": 0.10,
                "Giulia Ferrari": 0.08, "Stefano Gallo": 0.09}
BASE_RISK = 0.015


def _pick(rng: random.Random, weighted):
    items, weights = zip(*weighted)
    return rng.choices(items, weights=weights, k=1)[0]


def _work_time(rng: random.Random, day: datetime) -> datetime:
    hour = min(max(rng.gauss(12.5, 2.6), 7.2), 19.5)
    return day.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(
        hours=hour, seconds=rng.randint(0, 59), microseconds=rng.randint(0, 999_999))


def _plan(rng: random.Random, roster: dict, days: int, now: datetime) -> list[dict]:
    events = []
    for offset in range(days, -1, -1):
        day = now - timedelta(days=offset)
        weekend = day.weekday() >= 5
        for user in roster["users"]:
            activity = 1.6 if user["team"] in ("Engineering", "Customer Support") else 1.0
            mean = (0.6 if weekend else 7.0) * activity * rng.uniform(0.5, 1.5)
            for _ in range(max(0, int(rng.gauss(mean, mean ** 0.5)))):
                ts = _work_time(rng, day)
                if ts >= now:
                    continue
                risky = rng.random() < RISK_PROFILE.get(user["name"], BASE_RISK)
                events.append({"ts": ts, "user": user, "risky": risky})
    # One burst: a support agent pastes a batch of customer records, which trips the volume rule.
    burst_user = next(u for u in roster["users"] if u["name"] == "Zofia Kowalska")
    burst_start = (now - timedelta(days=2)).replace(hour=14, minute=5, second=0, microsecond=0)
    for i in range(9):
        events.append({"ts": burst_start + timedelta(minutes=2 * i, seconds=rng.randint(0, 50)), "user": burst_user,
                       "risky": True, "template": corpus.RISKY[0][0]})
    return sorted(events, key=lambda e: e["ts"])


async def seed(days: int | None = None, seed_value: int = 20261113) -> int:
    days = days or settings.demo_seed_days
    rng = random.Random(seed_value)
    roster = synth.load_roster()
    now = utcnow()
    async with SessionLocal() as session:
        apps = {a.slug: a for a in (await session.execute(select(Application))).scalars()}
        pols = {p.id: p for p in (await session.execute(select(Policy))).scalars()}
        standard = next(p for p in pols.values() if p.is_default)
        if not standard.custom_terms:
            standard.custom_terms = list(corpus.CUSTOM_TERMS)
            for p in pols.values():
                p.custom_terms = list(corpus.CUSTOM_TERMS)
            await session.commit()
        views = {slug: to_view(pols.get(a.policy_id) or standard) for slug, a in apps.items()}
    refs = {}
    for user in roster["users"]:
        refs[user["email"]] = await directory.ensure_user(
            user["email"], email=user["email"], name=user["name"], team=user["team"], title=user["title"],
            source="app", github_login=user.get("github"))

    events = _plan(rng, roster, days, now)
    log.info("seeding %d synthetic interactions over %d days", len(events), days)
    for index, event in enumerate(events):
        user = event["user"]
        slug = _pick(rng, TEAM_APPS[user["team"]])
        app, policy = apps[slug], views[slug]
        model = _pick(rng, APP_MODELS[slug])
        protocol, provider = PROTOCOLS["claude" if model.startswith("claude") else "gpt"]
        if event["risky"]:
            template = event.get("template")
            if template is None:
                candidates = [(t, w) for t, teams, w in corpus.RISKY if user["team"] in teams] or [
                    (t, w) for t, _, w in corpus.RISKY]
                template = _pick(rng, candidates)
            prompt = synth.fill(template, rng)
        else:
            pool = corpus.BENIGN[user["team"]] * 3 + corpus.BENIGN["general"]
            prompt = rng.choice(pool)
        segments = [Segment(prompt, "user")]
        detected, _ = await engine.scan_segments(segments, policy.custom_terms)
        findings, decision = apply_policy(policy, detected)
        action = {"block": "blocked", "mask": "masked"}.get(decision.enforced, "allowed")
        forwarded = prompt
        if action == "masked":
            forwarded = Redactor().apply(prompt, [f for f in findings if f.action == "mask"])
        response = "" if action == "blocked" else rng.choice(corpus.RESPONSES)
        upstream = 0.0 if action == "blocked" else rng.lognormvariate(6.9, 0.45)
        overhead = rng.uniform(1.2, 4.5) + len(prompt) / 900
        ref = refs[user["email"]]
        await recorder.persist(Record(
            user_id=ref.id, user_label=ref.label, app_id=app.id, app_name=app.name, policy=policy, ts=event["ts"],
            protocol=protocol, provider=provider, model=model, stream=rng.random() < 0.7, action=action,
            would_action=decision.would if decision.would != "allow" and decision.enforced == "allow" else None,
            segments=segments, findings=findings, response_text=response,
            forwarded_sha256=hashlib.sha256(forwarded.encode()).hexdigest(),
            input_tokens=None if action == "blocked" else len(prompt) // 4 + rng.randint(180, 900),
            output_tokens=None if action == "blocked" else rng.randint(60, 700),
            latency_ms=upstream + overhead, overhead_ms=overhead, upstream_ms=upstream,
            upstream_status=None if action == "blocked" else 200,
            token_jti=None), notify=False)
        if index and index % 1000 == 0:
            log.info("  %d of %d", index, len(events))

    async with SessionLocal() as session:
        session.add(Setting(key="demo_data", value={"loaded_at": now.isoformat(), "interactions": len(events),
                                                    "days": days, "company": roster["company"]}))
        await session.commit()
    return len(events)


async def work_the_inbox() -> None:
    """Close older demo alerts so the inbox looks like one that is being worked, not a backlog."""
    now = utcnow()
    cutoff = now - timedelta(days=2)
    async with SessionLocal() as session:
        old = (await session.execute(select(Alert).where(Alert.created_at < cutoff, Alert.status == "open"))).scalars().all()
        for i, alert in enumerate(old):
            alert.status = "false_positive" if i % 9 == 0 else "resolved"
            session.add(AlertEvent(alert_id=alert.id, ts=alert.last_seen_at + timedelta(hours=3),
                                   actor="demo data", action=alert.status,
                                   note="Closed by the demo seeder to illustrate a worked inbox."))
        recent = (await session.execute(select(Alert).where(
            Alert.created_at >= cutoff, Alert.created_at < now - timedelta(hours=20), Alert.status == "open"))).scalars().all()
        for i, alert in enumerate(recent):
            if i % 3 == 0:
                alert.status = "acknowledged"
                alert.assignee = settings.admin_email
                session.add(AlertEvent(alert_id=alert.id, ts=alert.last_seen_at + timedelta(hours=1),
                                       actor="demo data", action="acknowledged", note=""))
        await session.commit()


async def seed_if_empty() -> bool:
    async with SessionLocal() as session:
        if (await session.execute(select(func.count(RequestLog.id)))).scalar_one() > 0:
            return False
    count = await seed()
    log.info("demo data ready: %d interactions", count)
    return True


async def _main() -> None:
    parser = argparse.ArgumentParser(description="Load synthetic demo data")
    parser.add_argument("--days", type=int, default=settings.demo_seed_days)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    await init_models()
    await bootstrap()
    print(f"seeded {await seed(args.days)} interactions")
    await work_the_inbox()


if __name__ == "__main__":
    asyncio.run(_main())
