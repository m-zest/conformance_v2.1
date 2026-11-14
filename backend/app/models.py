"""Database schema."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, UTCDateTime, utcnow


def new_id() -> str:
    return uuid.uuid4().hex[:20]


class User(Base):
    """A monitored end user of AI tools (not a dashboard account)."""

    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(20), primary_key=True, default=new_id)
    external_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(255))
    team: Mapped[str | None] = mapped_column(String(120), index=True)
    title: Mapped[str | None] = mapped_column(String(160))
    github_login: Mapped[str | None] = mapped_column(String(120), index=True)
    source: Mapped[str] = mapped_column(String(20), default="app")
    first_seen: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Policy(Base):
    __tablename__ = "policies"
    id: Mapped[str] = mapped_column(String(20), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    mode: Mapped[str] = mapped_column(String(10), default="monitor")  # monitor | enforce
    rules: Mapped[dict] = mapped_column(JSON, default=dict)  # category -> allow|log|mask|block
    custom_terms: Mapped[list] = mapped_column(JSON, default=list)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_by: Mapped[str | None] = mapped_column(String(255))


class Application(Base):
    """An AI tool. kind=gateway is governed inline, kind=connector is observed from vendor logs."""

    __tablename__ = "applications"
    id: Mapped[str] = mapped_column(String(20), primary_key=True, default=new_id)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(12), default="gateway")
    vendor: Mapped[str] = mapped_column(String(80), default="Internal")
    description: Mapped[str] = mapped_column(Text, default="")
    owner: Mapped[str] = mapped_column(String(160), default="")
    policy_id: Mapped[str | None] = mapped_column(ForeignKey("policies.id"))
    trust_end_user: Mapped[bool] = mapped_column(Boolean, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class ApiKey(Base):
    __tablename__ = "api_keys"
    id: Mapped[str] = mapped_column(String(20), primary_key=True, default=new_id)
    app_id: Mapped[str] = mapped_column(ForeignKey("applications.id"), index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(160), default="")
    prefix: Mapped[str] = mapped_column(String(16))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    created_by: Mapped[str | None] = mapped_column(String(255))
    last_used_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


class RequestLog(Base):
    """One AI interaction: a governed gateway request or an observed vendor interaction."""

    __tablename__ = "requests"
    id: Mapped[str] = mapped_column(String(20), primary_key=True, default=new_id)
    ts: Mapped[datetime] = mapped_column(UTCDateTime, index=True, default=utcnow)
    source: Mapped[str] = mapped_column(String(20), default="gateway", index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    app_id: Mapped[str | None] = mapped_column(ForeignKey("applications.id"), index=True)
    protocol: Mapped[str] = mapped_column(String(24), default="")
    provider: Mapped[str] = mapped_column(String(24), default="")
    model: Mapped[str] = mapped_column(String(120), default="")
    host_app: Mapped[str | None] = mapped_column(String(60))
    stream: Mapped[bool] = mapped_column(Boolean, default=False)
    mode: Mapped[str] = mapped_column(String(10), default="monitor")
    action: Mapped[str] = mapped_column(String(12), default="allowed", index=True)
    would_action: Mapped[str | None] = mapped_column(String(12))
    severity: Mapped[int] = mapped_column(Integer, default=0, index=True)
    finding_count: Mapped[int] = mapped_column(Integer, default=0)
    new_finding_count: Mapped[int] = mapped_column(Integer, default=0)
    categories: Mapped[str] = mapped_column(String(255), default="")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    usage_estimated: Mapped[bool] = mapped_column(Boolean, default=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    overhead_ms: Mapped[float] = mapped_column(Float, default=0.0)
    upstream_ms: Mapped[float] = mapped_column(Float, default=0.0)
    upstream_status: Mapped[int | None] = mapped_column(Integer)
    prompt_chars: Mapped[int] = mapped_column(Integer, default=0)
    prompt_text: Mapped[str | None] = mapped_column(Text)
    response_text: Mapped[str | None] = mapped_column(Text)
    prompt_sha256: Mapped[str] = mapped_column(String(64), default="")
    response_sha256: Mapped[str] = mapped_column(String(64), default="")
    policy_id: Mapped[str | None] = mapped_column(String(20))
    policy_version: Mapped[int | None] = mapped_column(Integer)
    token_jti: Mapped[str | None] = mapped_column(String(40))
    error: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (Index("ix_requests_user_ts", "user_id", "ts"), Index("ix_requests_app_ts", "app_id", "ts"))


class Finding(Base):
    __tablename__ = "findings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), index=True)
    ts: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    user_id: Mapped[str | None] = mapped_column(String(20), index=True)
    app_id: Mapped[str | None] = mapped_column(String(20), index=True)
    direction: Mapped[str] = mapped_column(String(10), default="prompt")
    detector: Mapped[str] = mapped_column(String(24))
    category: Mapped[str] = mapped_column(String(32), index=True)
    entity_type: Mapped[str] = mapped_column(String(48))
    severity: Mapped[int] = mapped_column(Integer, default=1)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    action: Mapped[str] = mapped_column(String(8), default="log")
    preview: Mapped[str] = mapped_column(String(80), default="")
    fingerprint: Mapped[str] = mapped_column(String(32), default="")
    is_new: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class SeenFingerprint(Base):
    """Keyed hashes of sensitive values already seen per user. Used to separate new exposure from repeats."""

    __tablename__ = "seen_fingerprints"
    user_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(32), primary_key=True)
    first_seen: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    count: Mapped[int] = mapped_column(Integer, default=1)


class AlertRule(Base):
    __tablename__ = "alert_rules"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(16))  # finding | volume
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    position: Mapped[int] = mapped_column(Integer, default=0)


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[str] = mapped_column(String(20), primary_key=True, default=new_id)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    rule_id: Mapped[str] = mapped_column(String(40), index=True)
    severity: Mapped[int] = mapped_column(Integer, default=2, index=True)
    title: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(20), default="gateway")
    user_id: Mapped[str | None] = mapped_column(String(20), index=True)
    app_id: Mapped[str | None] = mapped_column(String(20), index=True)
    request_id: Mapped[str | None] = mapped_column(String(20))
    last_request_id: Mapped[str | None] = mapped_column(String(20))
    occurrences: Mapped[int] = mapped_column(Integer, default=1)
    entity_types: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)
    assignee: Mapped[str | None] = mapped_column(String(255))
    dedupe_key: Mapped[str] = mapped_column(String(40), index=True)


class AlertEvent(Base):
    __tablename__ = "alert_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[str] = mapped_column(ForeignKey("alerts.id", ondelete="CASCADE"), index=True)
    ts: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    actor: Mapped[str] = mapped_column(String(255), default="system")
    action: Mapped[str] = mapped_column(String(40))
    note: Mapped[str] = mapped_column(Text, default="")


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    channel: Mapped[str] = mapped_column(String(20))
    alert_id: Mapped[str | None] = mapped_column(String(20))
    subject: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(10))
    detail: Mapped[str] = mapped_column(Text, default="")


class LedgerEntry(Base):
    """Append-only hash chain over request records and administrative actions."""

    __tablename__ = "ledger"
    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    record_type: Mapped[str] = mapped_column(String(16))
    record_id: Mapped[str] = mapped_column(String(40), index=True)
    payload_hash: Mapped[str] = mapped_column(String(64))
    prev_hash: Mapped[str] = mapped_column(String(64))
    entry_hash: Mapped[str] = mapped_column(String(64))
    signature: Mapped[str] = mapped_column(String(200), default="")
    key_id: Mapped[str] = mapped_column(String(32), default="")


class LedgerHead(Base):
    __tablename__ = "ledger_head"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seq: Mapped[int] = mapped_column(Integer, default=0)
    entry_hash: Mapped[str] = mapped_column(String(64))


class AuditLog(Base):
    """Administrative actions taken in the dashboard."""

    __tablename__ = "audit_log"
    id: Mapped[str] = mapped_column(String(20), primary_key=True, default=new_id)
    ts: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    actor: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(60))
    target: Mapped[str] = mapped_column(String(255), default="")
    details: Mapped[dict] = mapped_column(JSON, default=dict)


class Admin(Base):
    """Dashboard account."""

    __tablename__ = "admins"
    id: Mapped[str] = mapped_column(String(20), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), default="")
    role: Mapped[str] = mapped_column(String(12), default="analyst")  # admin | analyst | auditor
    password_hash: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


class Connector(Base):
    __tablename__ = "connectors"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    app_id: Mapped[str | None] = mapped_column(String(20))
    mode: Mapped[str] = mapped_column(String(10), default="disabled")  # disabled | demo | live
    cursor: Mapped[dict] = mapped_column(JSON, default=dict)
    last_sync_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_status: Mapped[str] = mapped_column(String(12), default="never")
    last_error: Mapped[str] = mapped_column(Text, default="")
    items_synced: Mapped[int] = mapped_column(Integer, default=0)


class CopilotSeat(Base):
    __tablename__ = "copilot_seats"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    connector_id: Mapped[str] = mapped_column(String(40), index=True)
    login: Mapped[str] = mapped_column(String(120))
    user_id: Mapped[str | None] = mapped_column(String(20))
    plan: Mapped[str] = mapped_column(String(40), default="")
    assigned_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_activity_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_activity_editor: Mapped[str] = mapped_column(String(160), default="")

    __table_args__ = (UniqueConstraint("connector_id", "login"),)


class CopilotUsageDaily(Base):
    __tablename__ = "copilot_usage_daily"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    connector_id: Mapped[str] = mapped_column(String(40), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    login: Mapped[str] = mapped_column(String(120))
    user_id: Mapped[str | None] = mapped_column(String(20))
    interactions: Mapped[int] = mapped_column(Integer, default=0)
    code_generations: Mapped[int] = mapped_column(Integer, default=0)
    code_acceptances: Mapped[int] = mapped_column(Integer, default=0)
    loc_suggested: Mapped[int] = mapped_column(Integer, default=0)
    loc_accepted: Mapped[int] = mapped_column(Integer, default=0)
    used_chat: Mapped[bool] = mapped_column(Boolean, default=False)
    used_agent: Mapped[bool] = mapped_column(Boolean, default=False)
    top_ide: Mapped[str] = mapped_column(String(60), default="")
    top_language: Mapped[str] = mapped_column(String(60), default="")
    top_model: Mapped[str] = mapped_column(String(80), default="")

    __table_args__ = (UniqueConstraint("connector_id", "day", "login"),)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
