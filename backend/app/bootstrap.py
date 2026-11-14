"""First-start data: default policies, alert rules, the admin account and built-in tool entries."""
from __future__ import annotations

import logging

from sqlalchemy import func, select

from .alerts import DEFAULT_ALERT_RULES
from .config import settings
from .db import SessionLocal
from .models import Admin, AlertRule, ApiKey, Application, Connector, Policy
from .policy import DEFAULT_RULES, STRICT_RULES
from .security import hash_key, hash_password

log = logging.getLogger("conformance.bootstrap")

POLICIES = [
    {"name": "Standard", "mode": "enforce", "is_default": True, "rules": DEFAULT_RULES,
     "description": "Blocks credentials, masks financial identifiers, national IDs and health data, "
                    "and logs contact details, names, confidentiality markers and injection attempts."},
    {"name": "Monitor only", "mode": "monitor", "is_default": False, "rules": DEFAULT_RULES,
     "description": "Same rules as Standard but nothing is modified or blocked. Use it for the first weeks "
                    "of a rollout to measure what enforcement would do."},
    {"name": "Strict", "mode": "enforce", "is_default": False, "rules": STRICT_RULES,
     "description": "For tools that face customers or handle regulated data. Also masks contact details and "
                    "blocks confidential content, injection attempts and unsafe requests."},
]

CONNECTOR_APPS = [
    {"id": "m365-copilot", "slug": "m365-copilot", "name": "Microsoft 365 Copilot", "vendor": "Microsoft",
     "description": "Observed through the Microsoft Graph interaction export. No inline control."},
    {"id": "github-copilot", "slug": "github-copilot", "name": "GitHub Copilot", "vendor": "GitHub",
     "description": "Observed through seat and usage reports. Prompt content is not available from GitHub."},
]

DEMO_APPS = [
    {"slug": "internal-assistant", "name": "Internal Assistant", "policy": "Standard", "owner": "Digital Workplace",
     "description": "Company chat assistant for all employees."},
    {"slug": "support-desk", "name": "Support Desk Drafting", "policy": "Strict", "owner": "Customer Support",
     "description": "Drafts replies to customer tickets."},
    {"slug": "contract-review", "name": "Contract Review", "policy": "Strict", "owner": "Legal",
     "description": "Summarises and compares contract clauses."},
    {"slug": "developer-tools", "name": "Developer Tools (Claude Code, Codex)", "policy": "Monitor only",
     "owner": "Engineering Platform", "description": "Coding assistants routed through the gateway."},
]


async def run() -> None:
    async with SessionLocal() as session:
        if (await session.execute(select(func.count(Policy.id)))).scalar_one() == 0:
            for p in POLICIES:
                session.add(Policy(name=p["name"], mode=p["mode"], is_default=p["is_default"],
                                   rules=dict(p["rules"]), description=p["description"], updated_by="system"))
            log.info("created default policies")
        existing_rules = set((await session.execute(select(AlertRule.id))).scalars())
        for position, rule in enumerate(DEFAULT_ALERT_RULES):
            if rule["id"] not in existing_rules:
                session.add(AlertRule(id=rule["id"], name=rule["name"], description=rule["description"],
                                      kind=rule["kind"], params=rule["params"], position=position))
        if (await session.execute(select(func.count(Admin.id)))).scalar_one() == 0:
            session.add(Admin(email=settings.admin_email, name="Administrator", role="admin",
                              password_hash=hash_password(settings.admin_password)))
            log.info("created admin account %s", settings.admin_email)
        await session.flush()

        existing_apps = set((await session.execute(select(Application.slug))).scalars())
        for app in CONNECTOR_APPS:
            if app["slug"] not in existing_apps:
                session.add(Application(id=app["id"], slug=app["slug"], name=app["name"], kind="connector",
                                        vendor=app["vendor"], description=app["description"], trust_end_user=False))
        modes = {"m365-copilot": settings.m365_mode, "github-copilot": settings.github_mode}
        existing_connectors = {c.id: c for c in (await session.execute(select(Connector))).scalars()}
        for app in CONNECTOR_APPS:
            connector = existing_connectors.get(app["id"])
            if connector is None:
                session.add(Connector(id=app["id"], name=app["name"], app_id=app["id"], mode=modes[app["id"]]))
            elif connector.mode != modes[app["id"]]:
                connector.mode = modes[app["id"]]

        if settings.demo_mode:
            policies = {p.name: p.id for p in (await session.execute(select(Policy))).scalars()}
            for app in DEMO_APPS:
                if app["slug"] not in existing_apps:
                    session.add(Application(slug=app["slug"], name=app["name"], kind="gateway", vendor="Internal",
                                            description=app["description"], owner=app["owner"],
                                            policy_id=policies.get(app["policy"]), trust_end_user=True))
            await session.flush()
            if settings.demo_app_key:
                digest = hash_key(settings.demo_app_key)
                if (await session.execute(select(ApiKey).where(ApiKey.key_hash == digest))).first() is None:
                    apps = {a.slug: a.id for a in (await session.execute(select(Application))).scalars()}
                    session.add(ApiKey(app_id=apps["internal-assistant"], name="Demo key from DEMO_APP_KEY",
                                       prefix=settings.demo_app_key[:10], key_hash=digest, created_by="system"))
        await session.commit()
