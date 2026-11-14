"""Caller identification for the gateway.

Three ways to establish who is calling:
  1. Application key. The tool authenticates with one key and, if it is marked
     as trusted, asserts the signed-in user in the X-End-User headers.
  2. Personal key. The key is bound to one user (developer tools).
  3. OIDC token. A JWT from the company identity provider, verified against
     its JWKS. Used when developer tools obtain tokens through SSO.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import httpx
import jwt
from fastapi import Request
from sqlalchemy import select, update

from ..config import settings
from ..db import SessionLocal, utcnow
from ..models import ApiKey, Application, User
from ..security import KEY_PREFIX, hash_key


class AuthError(Exception):
    def __init__(self, message: str, status: int = 401) -> None:
        super().__init__(message)
        self.status = status


@dataclass
class AppRef:
    id: str
    slug: str
    name: str
    trust_end_user: bool


@dataclass
class UserRef:
    id: str
    label: str


@dataclass
class Caller:
    app: AppRef
    auth: str                      # app_key | personal_key | oidc
    user: UserRef | None = None    # set when the credential itself identifies the user
    claims: dict | None = None


class OidcVerifier:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client
        self._keys: dict[str, jwt.PyJWK] = {}
        self._fetched = 0.0

    @property
    def enabled(self) -> bool:
        return bool(settings.oidc_issuer)

    async def _refresh(self) -> None:
        client = self._client or httpx.AsyncClient(timeout=10)
        try:
            url = settings.oidc_jwks_url
            if not url:
                conf = await client.get(settings.oidc_issuer.rstrip("/") + "/.well-known/openid-configuration")
                conf.raise_for_status()
                url = conf.json()["jwks_uri"]
            resp = await client.get(url)
            resp.raise_for_status()
            self._keys = {k["kid"]: jwt.PyJWK(k) for k in resp.json().get("keys", []) if k.get("kid")}
            self._fetched = time.monotonic()
        finally:
            if self._client is None:
                await client.aclose()

    async def verify(self, token: str) -> dict:
        try:
            kid = jwt.get_unverified_header(token).get("kid")
        except jwt.PyJWTError as exc:
            raise AuthError("Malformed bearer token") from exc
        if kid not in self._keys and time.monotonic() - self._fetched > 30:
            try:
                await self._refresh()
            except Exception as exc:
                raise AuthError("Identity provider keys are not reachable", 503) from exc
        key = self._keys.get(kid)
        if key is None:
            raise AuthError("Token was signed with an unknown key")
        try:
            return jwt.decode(token, key.key, algorithms=["RS256", "ES256"], issuer=settings.oidc_issuer,
                              audience=settings.oidc_audience or None,
                              options={"verify_aud": bool(settings.oidc_audience)})
        except jwt.PyJWTError as exc:
            raise AuthError(f"Token rejected: {exc}") from exc


class Directory:
    """Resolves and caches applications, keys and end users."""

    def __init__(self) -> None:
        self._keys: dict[str, tuple[float, AppRef, UserRef | None, str]] = {}
        self._apps: dict[str, tuple[float, AppRef]] = {}
        self._users: dict[str, tuple[float, UserRef, tuple]] = {}
        self._key_touch: dict[str, float] = {}
        self._pending_touch: set[str] = set()
        self.oidc = OidcVerifier()

    def invalidate(self) -> None:
        self._keys.clear()
        self._apps.clear()

    async def _lookup_key(self, raw: str) -> tuple[AppRef, UserRef | None]:
        digest = hash_key(raw)
        now = time.monotonic()
        hit = self._keys.get(digest)
        if hit and now - hit[0] < 30:
            self._touch(hit[3], now)
            return hit[1], hit[2]
        async with SessionLocal() as session:
            row = (await session.execute(
                select(ApiKey, Application).join(Application, Application.id == ApiKey.app_id)
                .where(ApiKey.key_hash == digest))).first()
            if row is None:
                raise AuthError("Unknown gateway key")
            key, app = row
            if key.revoked_at is not None:
                raise AuthError("This gateway key has been revoked")
            if key.expires_at is not None and key.expires_at < utcnow():
                raise AuthError("This gateway key has expired")
            if not app.enabled:
                raise AuthError("This application is disabled", 403)
            user = None
            if key.user_id:
                u = (await session.execute(select(User).where(User.id == key.user_id))).scalar_one_or_none()
                if u:
                    user = UserRef(u.id, u.display_name or u.email or u.external_id)
        app_ref = AppRef(app.id, app.slug, app.name, app.trust_end_user)
        self._keys[digest] = (now, app_ref, user, key.id)
        self._touch(key.id, now)
        return app_ref, user

    def _touch(self, key_id: str, now: float) -> None:
        if now - self._key_touch.get(key_id, 0) > 60:
            self._key_touch[key_id] = now
            self._pending_touch.add(key_id)

    async def flush_key_usage(self) -> None:
        pending, self._pending_touch = self._pending_touch, set()
        if not pending:
            return
        async with SessionLocal() as session:
            await session.execute(update(ApiKey).where(ApiKey.id.in_(pending)).values(last_used_at=utcnow()))
            await session.commit()

    async def app_by_slug(self, slug: str) -> AppRef | None:
        now = time.monotonic()
        hit = self._apps.get(slug)
        if hit and now - hit[0] < 30:
            return hit[1]
        async with SessionLocal() as session:
            app = (await session.execute(select(Application).where(
                Application.slug == slug, Application.enabled.is_(True)))).scalar_one_or_none()
        if app is None:
            return None
        ref = AppRef(app.id, app.slug, app.name, app.trust_end_user)
        self._apps[slug] = (now, ref)
        return ref

    async def ensure_user(self, external_id: str, *, email: str | None = None, name: str | None = None,
                          team: str | None = None, source: str = "app", title: str | None = None,
                          github_login: str | None = None) -> UserRef:
        external_id = external_id.strip().lower()[:255]
        profile = (name, team)
        now = time.monotonic()
        hit = self._users.get(external_id)
        if hit and now - hit[0] < 300 and (hit[2] == profile or profile == (None, None)):
            return hit[1]
        async with SessionLocal() as session:
            user = (await session.execute(select(User).where(User.external_id == external_id))).scalar_one_or_none()
            if user is None:
                user = User(external_id=external_id, email=email or (external_id if "@" in external_id else None),
                            display_name=name, team=team, source=source, title=title, github_login=github_login)
                session.add(user)
            else:
                if name and user.display_name != name:
                    user.display_name = name
                if team and user.team != team:
                    user.team = team
                if title and not user.title:
                    user.title = title
                if github_login and not user.github_login:
                    user.github_login = github_login
            await session.commit()
            ref = UserRef(user.id, user.display_name or user.email or user.external_id)
        self._users[external_id] = (now, ref, profile)
        return ref

    async def identify(self, request: Request) -> Caller:
        token = ""
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
        token = token or request.headers.get("x-api-key", "") or request.headers.get("api-key", "")
        if not token:
            raise AuthError("Missing credentials. Send a gateway key as a bearer token or x-api-key header.")
        if token.startswith(KEY_PREFIX):
            app, user = await self._lookup_key(token)
            return Caller(app=app, auth="personal_key" if user else "app_key", user=user)
        if self.oidc.enabled and token.count(".") == 2:
            claims = await self.oidc.verify(token)
            slug = request.headers.get("x-gateway-app") or settings.oidc_default_app
            app = await self.app_by_slug(slug)
            if app is None:
                raise AuthError(f"Application '{slug}' is not registered", 403)
            email = claims.get(settings.oidc_email_claim) or claims.get("preferred_username") or claims.get("sub")
            user = await self.ensure_user(str(email), email=str(email) if "@" in str(email) else None,
                                          name=claims.get(settings.oidc_name_claim),
                                          team=claims.get(settings.oidc_team_claim), source="oidc")
            return Caller(app=app, auth="oidc", user=user, claims=claims)
        raise AuthError("Credential is not a valid gateway key")

    async def resolve_user(self, caller: Caller, request: Request, hint: str | None) -> UserRef:
        if caller.user is not None:
            return caller.user
        if caller.app.trust_end_user:
            asserted = request.headers.get("x-end-user") or hint
            if asserted:
                return await self.ensure_user(asserted, name=request.headers.get("x-end-user-name"),
                                              team=request.headers.get("x-end-user-team"), source="app")
        return await self.ensure_user(f"app:{caller.app.slug}", name=f"Unattributed ({caller.app.name})",
                                      source="service")


directory = Directory()
