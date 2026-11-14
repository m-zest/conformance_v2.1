"""The governed request path: identify, scan, decide, sign, forward, record."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from collections import defaultdict

import anyio
import httpx
from fastapi import Request
from fastapi.responses import Response, StreamingResponse

from ..config import settings
from ..detection.engine import Redactor, engine
from ..detection.model import entity_label
from ..policy import apply_policy, policies
from ..recorder import Record, recorder
from ..signing import TOKEN_HEADER, signer
from .adapters import ADAPTERS, Adapter
from .identity import AuthError, directory

log = logging.getLogger("conformance.gateway")

_DROP_HEADERS = {"content-length", "transfer-encoding", "connection", "content-encoding", "keep-alive", "server",
                 "date"}


def _reason_text(reasons: list[str]) -> str:
    return ", ".join(entity_label(r) for r in reasons[:4]) or "restricted content"


class Gateway:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(settings.upstream_timeout, connect=10.0),
                limits=httpx.Limits(max_connections=200, max_keepalive_connections=50))
        return self._client

    @client.setter
    def client(self, value: httpx.AsyncClient) -> None:
        self._client = value

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()

    async def handle(self, request: Request, protocol: str) -> Response:
        started = time.perf_counter()
        adapter = ADAPTERS[protocol]
        try:
            caller = await directory.identify(request)
        except AuthError as exc:
            return adapter.error(exc.status, "authentication_error", str(exc))

        raw = await request.body()
        if len(raw) > settings.max_body_bytes:
            return adapter.error(413, "invalid_request_error", "Request body is larger than the gateway accepts.")
        try:
            body = json.loads(raw)
            if not isinstance(body, dict):
                raise ValueError
        except ValueError:
            return adapter.error(400, "invalid_request_error", "Request body must be a JSON object.")

        user = await directory.resolve_user(caller, request, adapter.user_hint(body))
        policy = await policies.for_app(caller.app.id)
        segments = adapter.segments(body)
        detected, truncated = await engine.scan_segments(segments, policy.custom_terms)

        guard_task = None
        if engine.guard.enabled and policy.rules.get("content_safety") != "allow":
            last_user = next((s.text for s in reversed(segments) if s.role == "user" and s.text.strip()), "")
            if last_user and engine.guard.inline:
                detected += await engine.guard.classify(last_user)
            elif last_user:
                guard_task = asyncio.create_task(engine.guard.classify(last_user))

        findings, decision = apply_policy(policy, detected)
        record = Record(user_id=user.id, user_label=user.label, app_id=caller.app.id, app_name=caller.app.name,
                        policy=policy, protocol=adapter.protocol, provider=adapter.provider,
                        model=str(body.get("model") or ""), stream=bool(body.get("stream")), segments=segments,
                        findings=findings, guard_task=guard_task)
        if truncated:
            record.error = "request exceeded MAX_SCAN_CHARS, older content was not scanned"
        if decision.would != "allow" and decision.enforced == "allow":
            record.would_action = decision.would
        info = {"x-conformance-request-id": record.id, "x-conformance-findings": str(len(findings)),
                "x-conformance-policy-mode": policy.mode}

        if decision.enforced == "block":
            record.action = "blocked"
            record.forwarded_sha256 = hashlib.sha256(raw).hexdigest()
            record.overhead_ms = record.latency_ms = (time.perf_counter() - started) * 1000
            recorder.submit(record)
            message = (f"This request was blocked by the AI usage policy \"{policy.name}\" because it contains "
                       f"{_reason_text(decision.reasons)}. Remove that content and try again. "
                       f"Reference: {record.id}")
            return adapter.error(403, "policy_violation", message, {**info, "x-conformance-action": "blocked"})

        payload = raw
        if decision.enforced == "mask":
            redactor = Redactor()
            by_segment = defaultdict(list)
            for f in findings:
                if f.action == "mask":
                    by_segment[f.segment].append(f)
            for index, items in by_segment.items():
                seg = segments[index]
                if seg.setter is not None:
                    seg.setter(redactor.apply(seg.text, items))
            payload = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
            record.action = "masked"
        info["x-conformance-action"] = record.action

        headers = adapter.upstream_headers(request)
        if settings.signing_enabled:
            headers[TOKEN_HEADER] = signer.issue(
                request_id=record.id, subject=user.id, app=caller.app.slug, policy_id=policy.id,
                policy_version=policy.version, mode=policy.mode, decision=record.action, body=payload)
            record.token_jti = record.id
        record.forwarded_sha256 = hashlib.sha256(payload).hexdigest()
        record.overhead_ms = (time.perf_counter() - started) * 1000
        return await self._forward(request, adapter, record, payload, headers, info, started)

    async def _forward(self, request: Request, adapter: Adapter, record: Record, payload: bytes, headers: dict,
                       info: dict, started: float) -> Response:
        upstream_started = time.perf_counter()
        try:
            upstream_request = self.client.build_request("POST", adapter.upstream_url(), content=payload,
                                                         headers=headers, params=dict(request.query_params))
            resp = await self.client.send(upstream_request, stream=True)
        except httpx.HTTPError as exc:
            record.action = "error"
            record.error = f"upstream unreachable: {type(exc).__name__}"
            record.upstream_ms = (time.perf_counter() - upstream_started) * 1000
            record.latency_ms = (time.perf_counter() - started) * 1000
            recorder.submit(record)
            log.warning("upstream call failed for %s: %r", record.id, exc)
            return adapter.error(502, "api_error", "The gateway could not reach the model provider.", info)

        out_headers = {k: v for k, v in resp.headers.items() if k.lower() not in _DROP_HEADERS}
        out_headers.update(info)
        record.upstream_status = resp.status_code
        streaming = (record.stream and resp.status_code == 200
                     and "text/event-stream" in resp.headers.get("content-type", ""))

        if not streaming:
            try:
                content = await resp.aread()
            finally:
                await resp.aclose()
            record.upstream_ms = (time.perf_counter() - upstream_started) * 1000
            record.latency_ms = (time.perf_counter() - started) * 1000
            if resp.status_code == 200:
                try:
                    data = json.loads(content)
                    record.response_text, record.input_tokens, record.output_tokens = adapter.parse_response(data)
                    record.model = data.get("model") or record.model
                except (ValueError, AttributeError, TypeError):
                    pass
            else:
                record.error = f"upstream returned HTTP {resp.status_code}"
            recorder.submit(record)
            return Response(content, status_code=resp.status_code, headers=out_headers)

        parser = adapter.stream_parser()

        async def relay():
            try:
                async for chunk in resp.aiter_bytes():
                    parser.feed(chunk)
                    yield chunk
            except httpx.HTTPError as exc:
                record.error = f"stream interrupted: {type(exc).__name__}"
            finally:
                with anyio.CancelScope(shield=True):
                    await resp.aclose()
                record.response_text = parser.text
                record.input_tokens, record.output_tokens = parser.input_tokens, parser.output_tokens
                record.model = parser.model or record.model
                record.upstream_ms = (time.perf_counter() - upstream_started) * 1000
                record.latency_ms = (time.perf_counter() - started) * 1000
                recorder.submit(record)

        return StreamingResponse(relay(), status_code=200, headers=out_headers)

    async def passthrough(self, request: Request, protocol: str, url: str) -> Response:
        """Authenticated relay for auxiliary endpoints that generate no content (model list, token counting)."""
        adapter = ADAPTERS[protocol]
        try:
            caller = await directory.identify(request)
        except AuthError as exc:
            return adapter.error(exc.status, "authentication_error", str(exc))
        raw = await request.body()
        headers = adapter.upstream_headers(request)
        if settings.signing_enabled:
            subject = caller.user.id if caller.user else caller.app.slug
            headers[TOKEN_HEADER] = signer.issue(request_id=hashlib.sha256(raw + url.encode()).hexdigest()[:20],
                                                 subject=subject, app=caller.app.slug, policy_id="none",
                                                 policy_version=0, mode="passthrough", decision="allowed", body=raw)
        try:
            resp = await self.client.request(request.method, url, content=raw or None, headers=headers,
                                             params=dict(request.query_params))
        except httpx.HTTPError:
            return adapter.error(502, "api_error", "The gateway could not reach the model provider.")
        out_headers = {k: v for k, v in resp.headers.items() if k.lower() not in _DROP_HEADERS}
        return Response(resp.content, status_code=resp.status_code, headers=out_headers)


gateway = Gateway()
