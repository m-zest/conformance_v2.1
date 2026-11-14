"""Operator commands.

    python -m app.cli verify-ledger        check the audit ledger, exit code 1 if it is broken
    python -m app.cli create-key <slug>    create an application key for a registered tool
    python -m app.cli reset-password <email> <new password>
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys

from sqlalchemy import select

from . import ledger
from .db import SessionLocal, init_models
from .models import Admin, ApiKey, Application
from .security import audit, generate_gateway_key, hash_key, hash_password


async def verify_ledger() -> int:
    async with SessionLocal() as session:
        result = await ledger.verify(session)
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


async def create_key(slug: str, name: str) -> int:
    async with SessionLocal() as session:
        app = (await session.execute(select(Application).where(Application.slug == slug))).scalar_one_or_none()
        if app is None or app.kind != "gateway":
            print(f"No gateway tool with identifier '{slug}'", file=sys.stderr)
            return 1
        raw = generate_gateway_key()
        session.add(ApiKey(app_id=app.id, name=name, prefix=raw[:10], key_hash=hash_key(raw), created_by="cli"))
        await audit(session, "cli", "key.created", slug)
        await session.commit()
    print(raw)
    return 0


async def reset_password(email: str, password: str) -> int:
    if len(password) < 10:
        print("The password must have at least 10 characters", file=sys.stderr)
        return 1
    async with SessionLocal() as session:
        admin = (await session.execute(select(Admin).where(Admin.email == email.lower()))).scalar_one_or_none()
        if admin is None:
            print(f"No dashboard account for {email}", file=sys.stderr)
            return 1
        admin.password_hash = hash_password(password)
        admin.active = True
        await audit(session, "cli", "auth.password_reset", admin.email)
        await session.commit()
    print(f"Password updated for {email}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="Conformance operator commands")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify-ledger", help="verify the audit ledger")
    key = sub.add_parser("create-key", help="create an application key")
    key.add_argument("slug")
    key.add_argument("--name", default="Created from the command line")
    pw = sub.add_parser("reset-password", help="set a dashboard account password")
    pw.add_argument("email")
    pw.add_argument("password")
    args = parser.parse_args()

    async def run() -> int:
        await init_models()
        if args.command == "verify-ledger":
            return await verify_ledger()
        if args.command == "create-key":
            return await create_key(args.slug, args.name)
        return await reset_password(args.email, args.password)

    sys.exit(asyncio.run(run()))


if __name__ == "__main__":
    main()
