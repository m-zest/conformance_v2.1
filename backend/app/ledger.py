"""Tamper-evident audit ledger.

Every request record and administrative action is appended to a hash chain:
entry_hash = SHA-256(prev_hash | seq | record_type | record_id | payload_hash).
Each entry is signed with the gateway key. Verification recomputes the chain
and, where the underlying record still exists, recomputes its payload hash, so
both deletion from the chain and edits to stored records are detected.
"""
from __future__ import annotations

import hashlib
import json
from datetime import timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AuditLog, LedgerEntry, LedgerHead, RequestLog
from .signing import signer

GENESIS = "0" * 64


def canonical_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _ts(value) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def request_payload(r: RequestLog) -> dict:
    return {
        "id": r.id, "ts": _ts(r.ts), "source": r.source, "user": r.user_id or "",
        "app": r.app_id or "", "model": r.model, "mode": r.mode, "action": r.action,
        "would": r.would_action or "", "severity": r.severity, "findings": r.finding_count,
        "prompt_sha256": r.prompt_sha256, "response_sha256": r.response_sha256, "policy": r.policy_id or "",
        "policy_version": r.policy_version or 0, "jti": r.token_jti or "",
    }


def audit_payload(a: AuditLog) -> dict:
    return {"id": a.id, "ts": _ts(a.ts), "actor": a.actor, "action": a.action,
            "target": a.target, "details": a.details or {}}


def _entry_hash(prev_hash: str, seq: int, record_type: str, record_id: str, payload_hash: str) -> str:
    return hashlib.sha256(f"{prev_hash}|{seq}|{record_type}|{record_id}|{payload_hash}".encode()).hexdigest()


async def append(session: AsyncSession, record_type: str, record_id: str, payload: dict, ts) -> LedgerEntry:
    """Append one entry inside the caller's transaction. The head row is locked to serialise writers."""
    head = (await session.execute(select(LedgerHead).where(LedgerHead.id == 1).with_for_update())).scalar_one_or_none()
    if head is None:
        head = LedgerHead(id=1, seq=0, entry_hash=GENESIS)
        session.add(head)
        await session.flush()
    seq = head.seq + 1
    payload_hash = canonical_hash(payload)
    entry_hash = _entry_hash(head.entry_hash, seq, record_type, record_id, payload_hash)
    entry = LedgerEntry(seq=seq, ts=ts, record_type=record_type, record_id=record_id, payload_hash=payload_hash,
                        prev_hash=head.entry_hash, entry_hash=entry_hash,
                        signature=signer.sign(entry_hash.encode()), key_id=signer.kid)
    session.add(entry)
    head.seq = seq
    head.entry_hash = entry_hash
    return entry


async def verify(session: AsyncSession, batch: int = 2000) -> dict:
    prev = GENESIS
    checked = records_checked = 0
    last_seq = 0
    while True:
        entries = (await session.execute(
            select(LedgerEntry).where(LedgerEntry.seq > last_seq).order_by(LedgerEntry.seq).limit(batch))).scalars().all()
        if not entries:
            break
        req_ids = [e.record_id for e in entries if e.record_type == "request"]
        adm_ids = [e.record_id for e in entries if e.record_type == "admin"]
        reqs = {r.id: r for r in (await session.execute(
            select(RequestLog).where(RequestLog.id.in_(req_ids)))).scalars()} if req_ids else {}
        adms = {a.id: a for a in (await session.execute(
            select(AuditLog).where(AuditLog.id.in_(adm_ids)))).scalars()} if adm_ids else {}
        for e in entries:
            problem = None
            if e.seq != last_seq + 1:
                problem = f"missing entries between {last_seq} and {e.seq}"
            elif e.prev_hash != prev:
                problem = "previous hash does not match the preceding entry"
            elif _entry_hash(e.prev_hash, e.seq, e.record_type, e.record_id, e.payload_hash) != e.entry_hash:
                problem = "entry hash does not match its contents"
            elif e.key_id == signer.kid and not signer.verify(e.entry_hash.encode(), e.signature):
                problem = "signature is not valid"
            else:
                record = reqs.get(e.record_id) if e.record_type == "request" else adms.get(e.record_id)
                if record is not None:
                    records_checked += 1
                    payload = request_payload(record) if e.record_type == "request" else audit_payload(record)
                    if canonical_hash(payload) != e.payload_hash:
                        problem = f"stored {e.record_type} record {e.record_id} was modified after it was written"
            if problem:
                return {"valid": False, "entries_checked": checked, "records_checked": records_checked,
                        "failed_seq": e.seq, "record_id": e.record_id, "problem": problem}
            prev, last_seq = e.entry_hash, e.seq
            checked += 1
    return {"valid": True, "entries_checked": checked, "records_checked": records_checked, "head_hash": prev,
            "key_id": signer.kid}
