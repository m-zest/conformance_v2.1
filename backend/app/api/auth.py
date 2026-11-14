"""Dashboard sign-in and account management."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import get_session, utcnow
from ..models import Admin
from ..security import (ROLES, SESSION_COOKIE, admin_only, audit, create_session_token, current_admin,
                        hash_password, login_throttle, verify_password)
from .common import iso

router = APIRouter(prefix="/api", tags=["auth"])


class LoginBody(BaseModel):
    email: str
    password: str


class AdminBody(BaseModel):
    email: str
    name: str = ""
    role: str = "analyst"
    password: str = Field(min_length=10)


class AdminPatch(BaseModel):
    name: str | None = None
    role: str | None = None
    active: bool | None = None
    password: str | None = Field(default=None, min_length=10)


class PasswordBody(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10)


def _public(a: Admin) -> dict:
    return {"id": a.id, "email": a.email, "name": a.name, "role": a.role, "active": a.active,
            "created_at": iso(a.created_at), "last_login_at": iso(a.last_login_at)}


@router.post("/auth/login")
async def login(body: LoginBody, request: Request, response: Response, session: AsyncSession = Depends(get_session)):
    email = body.email.strip().lower()
    key = f"{email}|{request.client.host if request.client else ''}"
    if login_throttle.blocked(key):
        raise HTTPException(429, "Too many failed attempts. Try again in a few minutes.")
    admin = (await session.execute(select(Admin).where(Admin.email == email))).scalar_one_or_none()
    if admin is None or not admin.active or not verify_password(body.password, admin.password_hash):
        login_throttle.fail(key)
        raise HTTPException(401, "Email or password is incorrect")
    login_throttle.clear(key)
    admin.last_login_at = utcnow()
    await audit(session, admin.email, "auth.login")
    await session.commit()
    response.set_cookie(SESSION_COOKIE, create_session_token(admin), httponly=True, samesite="strict",
                        secure=settings.cookie_secure, max_age=settings.session_hours * 3600, path="/")
    return _public(admin)


@router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/auth/me")
async def me(admin: Admin = Depends(current_admin)):
    return {**_public(admin), "default_password": settings.using_default_admin_password
            and admin.email == settings.admin_email and verify_password(settings.admin_password, admin.password_hash)}


@router.post("/auth/password")
async def change_password(body: PasswordBody, admin: Admin = Depends(current_admin),
                          session: AsyncSession = Depends(get_session)):
    if not verify_password(body.current_password, admin.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    admin.password_hash = hash_password(body.new_password)
    await audit(session, admin.email, "auth.password_changed")
    await session.commit()
    return {"ok": True}


@router.get("/admins")
async def list_admins(_: Admin = Depends(admin_only), session: AsyncSession = Depends(get_session)):
    return [_public(a) for a in (await session.execute(select(Admin).order_by(Admin.created_at))).scalars()]


@router.post("/admins")
async def create_admin(body: AdminBody, actor: Admin = Depends(admin_only),
                       session: AsyncSession = Depends(get_session)):
    if body.role not in ROLES:
        raise HTTPException(400, "Unknown role")
    email = body.email.strip().lower()
    if (await session.execute(select(Admin).where(Admin.email == email))).first():
        raise HTTPException(409, "An account with this email already exists")
    admin = Admin(email=email, name=body.name, role=body.role, password_hash=hash_password(body.password))
    session.add(admin)
    await audit(session, actor.email, "admin.created", email, {"role": body.role})
    await session.commit()
    return _public(admin)


@router.patch("/admins/{admin_id}")
async def update_admin(admin_id: str, body: AdminPatch, actor: Admin = Depends(admin_only),
                       session: AsyncSession = Depends(get_session)):
    admin = (await session.execute(select(Admin).where(Admin.id == admin_id))).scalar_one_or_none()
    if admin is None:
        raise HTTPException(404, "Account not found")
    if admin.id == actor.id and (body.active is False or (body.role and body.role != "admin")):
        raise HTTPException(400, "You cannot remove your own administrator access")
    changes = {}
    if body.name is not None:
        admin.name = body.name
    if body.role is not None:
        if body.role not in ROLES:
            raise HTTPException(400, "Unknown role")
        admin.role = changes["role"] = body.role
    if body.active is not None:
        admin.active = changes["active"] = body.active
    if body.password:
        admin.password_hash = hash_password(body.password)
        changes["password_reset"] = True
    await audit(session, actor.email, "admin.updated", admin.email, changes)
    await session.commit()
    return _public(admin)
