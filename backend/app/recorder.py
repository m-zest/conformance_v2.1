"""Persists interactions: findings, ledger entry and alerts, off the request path.

The gateway hands a Record to submit() and returns to the caller immediately.
A single worker drains the queue, which keeps the ledger ordered and keeps
database latency out of the proxy path. Connectors and the demo seeder call
persist() directly.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime

import anyio
from sqlalchemy import select, update

from . import alerts as alert_engine
from . import ledger, notifications
from .config import settings
from .db import SessionLocal, utcnow
from .detection.engine import Redactor, Segment, engine, finalize_findings
from .detection.model import Finding as Detected
from .models import AlertRule, Finding, RequestLog, SeenFingerprint, User, new_id
from .policy import PolicyView, apply_policy
from .pricing import estimate_cost

log = logging.getLogger("conformance.recorder")


@dataclass
class Record:
    user_id: str | None
    user_label: str
    app_id: str | None
    app_name: str
    policy: PolicyView
    id: str = field(default_factory=new_id)
    ts: datetime = field(default_factory=utcnow)
    source: str = "gateway"
    external_id: str | None = None
    protocol: str = ""
    provider: str = ""
    model: str = ""
    host_app: str | None = None
    stream: bool = False
    action: str = "allowed"
    would_action: str | None = None
    segments: list[Segment] = field(default_factory=list)   # original (unredacted) request text
    findings: list[Detected] = field(default_factory=list)  # prompt findings, policy already applied
    response_text: str = ""
    forwarded_sha256: str = ""
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: float = 0.0
    overhead_ms: float = 0.0
    upstream_ms: float = 0.0
    upstream_status: int | None = None
    token_jti: str | None = None
    error: str | None = None
    guard_task: asyncio.Task | None = None


def _tail(segments: list[Segment]) -> list[tuple[int, Segment]]:
    """The new content of a request: everything after the last assistant turn."""
    last_assistant = max((i for i, s in enumerate(segments) if s.role == "assistant"), default=-1)
    tail = [(i, s) for i, s in enumerate(segments) if i > last_assistant and s.role in ("user", "tool")]
    return tail or [(i, s) for i, s in enumerate(segments) if s.role == "user"][-1:]


def stored_prompt(rec: Record) -> tuple[str | None, int]:
    tail = _tail(rec.segments)
    chars = sum(len(s.text) for s in rec.segments if s.role != "assistant")
    if settings.store_prompts == "none":
        return None, chars
    redactor = Redactor()
    parts = []
    for index, seg in tail:
        text = seg.text
        if settings.store_prompts != "full":
            text = redactor.apply(text, [f for f in rec.findings if f.segment == index])
        parts.append(text if seg.role == "user" else f"[tool result]\n{text}")
    joined = "\n\n".join(parts)
    if len(joined) > settings.max_stored_chars:
        joined = joined[: settings.max_stored_chars] + "\n[truncated]"
    return joined, chars


class Recorder:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[Record] = asyncio.Queue(maxsize=20_000)
        self._lock = asyncio.Lock()
        self._worker: asyncio.Task | None = None
        self._rules: list[AlertRule] | None = None
        self.dropped = 0
        self.failed = 0

    def start(self) -> None:
        if self._worker is None or self._worker.done():
            self._worker = asyncio.create_task(self._run(), name="recorder")

    async def stop(self) -> None:
        try:
            await asyncio.wait_for(self._queue.join(), timeout=20)
        except asyncio.TimeoutError:
            log.warning("recorder stopped with %d records still queued", self._queue.qsize())
        if self._worker:
            self._worker.cancel()

    def submit(self, record: Record) -> None:
        try:
            self._queue.put_nowait(record)
        except asyncio.QueueFull:
            self.dropped += 1
            log.error("record queue is full, dropping record %s", record.id)

    async def flush(self) -> None:
        await self._queue.join()

    def invalidate_rules(self) -> None:
        self._rules = None

    async def _run(self) -> None:
        while True:
            record = await self._queue.get()
            try:
                await self.persist(record)
            except Exception:
                self.failed += 1
                log.exception("failed to persist record %s", record.id)
            finally:
                self._queue.task_done()

    async def _response_findings(self, rec: Record) -> list[Detected]:
        found: list[Detected] = []
        if rec.response_text:
            text = rec.response_text[: settings.max_scan_chars]
            if len(text) > 30_000:
                raw = await anyio.to_thread.run_sync(lambda: engine.scan_text(text, rec.policy.custom_terms))
            else:
                raw = engine.scan_text(text, rec.policy.custom_terms)
            kept, _ = apply_policy(rec.policy, raw)
            for f in kept:
                f.direction = "response"
                f.action = "log"   # responses are monitored, not modified
            found += kept
        if rec.guard_task is not None:
            try:
                guard = await asyncio.wait_for(rec.guard_task, timeout=settings.guard_timeout + 1)
                kept, _ = apply_policy(rec.policy, guard)
                found += kept
            except Exception:
                pass
        return found

    async def persist(self, rec: Record, *, notify: bool = True) -> str:
        extra = await self._response_findings(rec)
        prompt_findings = rec.findings
        finalize_findings(prompt_findings)
        finalize_findings(extra)
        all_findings = prompt_findings + extra
        prompt_text, prompt_chars = stored_prompt(rec)
        response_text = None
        if rec.response_text and settings.store_responses and settings.store_prompts != "none":
            response_text = rec.response_text
            if settings.store_prompts != "full":
                response_text = Redactor().apply(response_text, [f for f in extra if f.direction == "response"])
            if len(response_text) > settings.max_stored_chars:
                response_text = response_text[: settings.max_stored_chars] + "\n[truncated]"
        usage_estimated = rec.input_tokens is None or rec.output_tokens is None
        input_tokens = rec.input_tokens if rec.input_tokens is not None else prompt_chars // 4
        output_tokens = rec.output_tokens if rec.output_tokens is not None else len(rec.response_text) // 4
        if rec.action == "blocked":
            input_tokens = output_tokens = 0
            usage_estimated = False

        new_alerts: list[dict] = []
        async with self._lock:
            async with SessionLocal() as session:
                async with session.begin():
                    await self._mark_new(session, rec, all_findings)
                    row = RequestLog(
                        id=rec.id, ts=rec.ts, source=rec.source, external_id=rec.external_id, user_id=rec.user_id,
                        app_id=rec.app_id, protocol=rec.protocol, provider=rec.provider, model=rec.model or "",
                        host_app=rec.host_app, stream=rec.stream, mode=rec.policy.mode, action=rec.action,
                        would_action=rec.would_action,
                        severity=max((f.severity for f in all_findings), default=0),
                        finding_count=len(all_findings),
                        new_finding_count=sum(1 for f in all_findings if f.is_new),
                        categories=",".join(sorted({f.category for f in all_findings}))[:255],
                        input_tokens=input_tokens, output_tokens=output_tokens, usage_estimated=usage_estimated,
                        cost_usd=estimate_cost(rec.model, input_tokens, output_tokens),
                        latency_ms=round(rec.latency_ms, 1), overhead_ms=round(rec.overhead_ms, 2),
                        upstream_ms=round(rec.upstream_ms, 1), upstream_status=rec.upstream_status,
                        prompt_chars=prompt_chars, prompt_text=prompt_text, response_text=response_text,
                        prompt_sha256=rec.forwarded_sha256,
                        response_sha256=hashlib.sha256(rec.response_text.encode()).hexdigest() if rec.response_text else "",
                        policy_id=rec.policy.id, policy_version=rec.policy.version, token_jti=rec.token_jti,
                        error=rec.error)
                    session.add(row)
                    await session.flush()   # the request row must exist before its findings
                    rows = [Finding(request_id=rec.id, ts=rec.ts, user_id=rec.user_id, app_id=rec.app_id,
                                    direction=f.direction, detector=f.detector, category=f.category,
                                    entity_type=f.entity_type, severity=f.severity, confidence=f.confidence,
                                    action=f.action, preview=f.preview[:80], fingerprint=f.fingerprint,
                                    is_new=f.is_new) for f in all_findings]
                    session.add_all(rows)
                    await session.flush()
                    await ledger.append(session, "request", row.id, ledger.request_payload(row), rec.ts)
                    if rows:
                        if self._rules is None:
                            self._rules = list((await session.execute(
                                select(AlertRule).order_by(AlertRule.position))).scalars())
                        created = await alert_engine.evaluate(session, row, rows, user_label=rec.user_label,
                                                              app_name=rec.app_name, rules=self._rules)
                        new_alerts = [alert_engine.alert_public(a, rec.user_label, rec.app_name) for a in created]
                    if rec.user_id:
                        await session.execute(update(User).where(User.id == rec.user_id, User.last_seen < rec.ts)
                                              .values(last_seen=rec.ts))
        if notify and new_alerts:
            asyncio.create_task(notifications.dispatch(new_alerts))
        return rec.id

    async def _mark_new(self, session, rec: Record, findings: list[Detected]) -> None:
        if not findings or not rec.user_id:
            return
        prints = {f.fingerprint for f in findings}
        seen = {s.fingerprint: s for s in (await session.execute(
            select(SeenFingerprint).where(SeenFingerprint.user_id == rec.user_id,
                                          SeenFingerprint.fingerprint.in_(prints)))).scalars()}
        first_in_request: set[str] = set()
        for f in findings:
            known = seen.get(f.fingerprint)
            if known is not None:
                f.is_new = False
                if f.fingerprint not in first_in_request:
                    known.count += 1
                    known.last_seen = rec.ts
                    first_in_request.add(f.fingerprint)
            elif f.fingerprint in first_in_request:
                f.is_new = False
            else:
                f.is_new = True
                first_in_request.add(f.fingerprint)
                session.add(SeenFingerprint(user_id=rec.user_id, fingerprint=f.fingerprint, first_seen=rec.ts,
                                            last_seen=rec.ts))


recorder = Recorder()
