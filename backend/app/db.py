"""Database engine, session factory and shared column types."""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from sqlalchemy import DateTime, event, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import TypeDecorator

from .config import settings


class UTCDateTime(TypeDecorator):
    """Timezone-aware datetime stored in UTC on every backend."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        value = value.astimezone(timezone.utc)
        return value.replace(tzinfo=None) if dialect.name == "sqlite" else value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _engine_kwargs(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"connect_args": {"timeout": 30}}
    return {"pool_size": 10, "max_overflow": 20, "pool_pre_ping": True}


engine = create_async_engine(settings.database_url, **_engine_kwargs(settings.database_url))
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
IS_POSTGRES = engine.dialect.name == "postgresql"

if not IS_POSTGRES:
    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


@asynccontextmanager
async def session_scope():
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_session():
    async with SessionLocal() as session:
        yield session


def time_bucket(column, unit: str):
    """SQL expression that truncates a timestamp to 'hour' or 'day' (UTC)."""
    if IS_POSTGRES:
        return func.date_trunc(unit, column, "UTC")
    fmt = "%Y-%m-%dT%H:00:00" if unit == "hour" else "%Y-%m-%dT00:00:00"
    return func.strftime(fmt, column)


def bucket_to_iso(value) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(value)[:19] + "Z"


async def init_models() -> None:
    from . import models  # noqa: F401  (register tables)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
