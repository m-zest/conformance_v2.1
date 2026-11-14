"""Dashboard authentication, password hashing, gateway key handling and admin audit logging."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from collections import defaultdict
from datetime import timedelta

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import ledger
from .config import settings
from .db import get_session, utcnow
from .models import Admin, AuditLog

SESSION_COOKIE = "conformance_session"
ROLES = ("admin", "analyst", "auditor")
KEY_PREFIX = "gw_"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_b64, digest_b64 = stored.split("$")
        salt, expected = base64.b64decode(salt_b64), base64.b64decode(digest_b64)
        actual = hashlib.scrypt(password.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def generate_gateway_key() -> str:
    return KEY_PREFIX + secrets.token_urlsafe(32)


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def create_session_token(admin: Admin) -> str:
    now = utcnow()
    return jwt.encode({"sub": admin.id, "role": admin.role, "email": admin.email, "iat": now,
                       "exp": now + timedelta(hours=settings.session_hours)}, settings.secret_key, algorithm="HS256")


class LoginThrottle:
    """Locks an account and address pair after repeated failures."""

    def __init__(self, limit: int = 5, window: int = 600) -> None:
        self.limit, self.window = limit, window
        self._failures: dict[str, list[float]] = defaultdict(list)

    def blocked(self, key: str) -> bool:
        now = time.monotonic()
        self._failures[key] = [t for t in self._failures[key] if now - t < self.window]
        return len(self._failures[key]) >= self.limit

    def fail(self, key: str) -> None:
        self._failures[key].append(time.monotonic())

    def clear(self, key: str) -> None:
        self._failures.pop(key, None)


login_throttle = LoginThrottle()


async def current_admin(request: Request, session: AsyncSession = Depends(get_session)) -> Admin:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(401, "Not signed in")
    try:
        claims = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Session expired")
    admin = (await session.execute(select(Admin).where(Admin.id == claims["sub"]))).scalar_one_or_none()
    if admin is None or not admin.active:
        raise HTTPException(401, "Account is not active")
    return admin


def require_role(*roles: str):
    async def dependency(admin: Admin = Depends(current_admin)) -> Admin:
        if admin.role not in roles:
            raise HTTPException(403, "Your role does not allow this action")
        return admin
    return dependency


any_role = require_role(*ROLES)
analyst_or_admin = require_role("admin", "analyst")
admin_only = require_role("admin")


async def audit(session: AsyncSession, actor: str, action: str, target: str = "", details: dict | None = None) -> None:
    """Record an administrative action and chain it into the ledger. Caller commits."""
    entry = AuditLog(actor=actor, action=action, target=target, details=details or {}, ts=utcnow())
    session.add(entry)
    await session.flush()
    await ledger.append(session, "admin", entry.id, ledger.audit_payload(entry), entry.ts)
