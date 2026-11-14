"""Wire protocol adapters.

Each adapter knows how to find the text inside a request body, write redacted
text back, read the model output from a response or an event stream, and shape
errors the way clients of that protocol expect.
"""
from __future__ import annotations

import json

from fastapi import Request
from fastapi.responses import JSONResponse

from ..config import settings
from ..detection.engine import Segment

_ROLE = {"developer": "system", "function": "tool"}
_TEXT_PARTS = {"text", "input_text", "output_text"}


def _setter(container, key):
    return lambda value: container.__setitem__(key, value)


def _content_segments(content, role: str, owner: dict, key: str = "content") -> list[Segment]:
    if isinstance(content, str):
        return [Segment(content, role, _setter(owner, key))]
    out = []
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") in _TEXT_PARTS and isinstance(part.get("text"), str):
                out.append(Segment(part["text"], role, _setter(part, "text")))
    return out


class StreamParser:
    """Reads a server-sent event stream on the side while the bytes are relayed unchanged."""

    def __init__(self) -> None:
        self._buffer = b""
        self.parts: list[str] = []
        self.input_tokens: int | None = None
        self.output_tokens: int | None = None
        self.model: str | None = None

    def feed(self, chunk: bytes) -> None:
        self._buffer += chunk
        while b"\n" in self._buffer:
            line, self._buffer = self._buffer.split(b"\n", 1)
            line = line.strip()
            if not line.startswith(b"data:"):
                continue
            payload = line[5:].strip()
            if not payload or payload == b"[DONE]":
                continue
            try:
                event = json.loads(payload)
            except ValueError:
                continue
            if isinstance(event, dict):
                self.handle(event)

    def handle(self, event: dict) -> None:  # pragma: no cover - overridden
        raise NotImplementedError

    @property
    def text(self) -> str:
        return "".join(self.parts)


class Adapter:
    protocol = ""
    provider = ""
    path = ""

    def segments(self, body: dict) -> list[Segment]:
        raise NotImplementedError

    def user_hint(self, body: dict) -> str | None:
        return None

    def upstream_url(self) -> str:
        raise NotImplementedError

    def upstream_headers(self, request: Request) -> dict:
        raise NotImplementedError

    def error(self, status: int, kind: str, message: str, headers: dict | None = None) -> JSONResponse:
        raise NotImplementedError

    def parse_response(self, data: dict) -> tuple[str, int | None, int | None]:
        raise NotImplementedError

    def stream_parser(self) -> StreamParser:
        raise NotImplementedError


def _openai_headers(request: Request) -> dict:
    headers = {"content-type": "application/json", "accept-encoding": "identity"}
    if settings.openai_auth_style == "api-key":
        headers["api-key"] = settings.openai_api_key
    else:
        headers["authorization"] = f"Bearer {settings.openai_api_key}"
    for name in ("openai-organization", "openai-project", "openai-beta", "accept"):
        if name in request.headers:
            headers[name] = request.headers[name]
    return headers


def _openai_error(status: int, kind: str, message: str, headers: dict | None = None) -> JSONResponse:
    return JSONResponse({"error": {"message": message, "type": kind, "param": None, "code": kind}},
                        status_code=status, headers=headers)


class _ChatStream(StreamParser):
    def handle(self, event: dict) -> None:
        self.model = event.get("model") or self.model
        for choice in event.get("choices") or []:
            delta = (choice.get("delta") or {}).get("content")
            if isinstance(delta, str):
                self.parts.append(delta)
        usage = event.get("usage")
        if isinstance(usage, dict):
            self.input_tokens = usage.get("prompt_tokens", self.input_tokens)
            self.output_tokens = usage.get("completion_tokens", self.output_tokens)


class OpenAIChatAdapter(Adapter):
    protocol = "openai.chat"
    provider = "openai"

    def segments(self, body: dict) -> list[Segment]:
        out: list[Segment] = []
        for msg in body.get("messages") or []:
            if not isinstance(msg, dict):
                continue
            role = _ROLE.get(msg.get("role", "user"), msg.get("role", "user"))
            out += _content_segments(msg.get("content"), role, msg)
        return out

    def user_hint(self, body: dict) -> str | None:
        user = body.get("user")
        return user if isinstance(user, str) and user else None

    def upstream_url(self) -> str:
        return f"{settings.openai_base_url}/chat/completions"

    upstream_headers = staticmethod(_openai_headers)
    error = staticmethod(_openai_error)

    def parse_response(self, data: dict) -> tuple[str, int | None, int | None]:
        text = "".join((c.get("message") or {}).get("content") or "" for c in data.get("choices") or []
                       if isinstance((c.get("message") or {}).get("content"), str))
        usage = data.get("usage") or {}
        return text, usage.get("prompt_tokens"), usage.get("completion_tokens")

    def stream_parser(self) -> StreamParser:
        return _ChatStream()


class _ResponsesStream(StreamParser):
    def handle(self, event: dict) -> None:
        kind = event.get("type")
        if kind == "response.output_text.delta" and isinstance(event.get("delta"), str):
            self.parts.append(event["delta"])
        elif kind in ("response.completed", "response.incomplete"):
            response = event.get("response") or {}
            usage = response.get("usage") or {}
            self.model = response.get("model") or self.model
            self.input_tokens = usage.get("input_tokens", self.input_tokens)
            self.output_tokens = usage.get("output_tokens", self.output_tokens)


class OpenAIResponsesAdapter(Adapter):
    protocol = "openai.responses"
    provider = "openai"

    def segments(self, body: dict) -> list[Segment]:
        out: list[Segment] = []
        if isinstance(body.get("instructions"), str):
            out.append(Segment(body["instructions"], "system", _setter(body, "instructions")))
        inp = body.get("input")
        if isinstance(inp, str):
            out.append(Segment(inp, "user", _setter(body, "input")))
        elif isinstance(inp, list):
            for item in inp:
                if not isinstance(item, dict):
                    continue
                kind = item.get("type", "message")
                if kind == "function_call_output" and isinstance(item.get("output"), str):
                    out.append(Segment(item["output"], "tool", _setter(item, "output")))
                elif kind == "message" or "role" in item:
                    role = _ROLE.get(item.get("role", "user"), item.get("role", "user"))
                    out += _content_segments(item.get("content"), role, item)
        return out

    def user_hint(self, body: dict) -> str | None:
        user = body.get("user") or body.get("safety_identifier")
        return user if isinstance(user, str) and user else None

    def upstream_url(self) -> str:
        return f"{settings.openai_base_url}/responses"

    upstream_headers = staticmethod(_openai_headers)
    error = staticmethod(_openai_error)

    def parse_response(self, data: dict) -> tuple[str, int | None, int | None]:
        parts = []
        for item in data.get("output") or []:
            for part in (item.get("content") or []) if isinstance(item, dict) else []:
                if isinstance(part, dict) and part.get("type") == "output_text":
                    parts.append(part.get("text") or "")
        usage = data.get("usage") or {}
        return "".join(parts), usage.get("input_tokens"), usage.get("output_tokens")

    def stream_parser(self) -> StreamParser:
        return _ResponsesStream()


class _AnthropicStream(StreamParser):
    def handle(self, event: dict) -> None:
        kind = event.get("type")
        if kind == "message_start":
            message = event.get("message") or {}
            usage = message.get("usage") or {}
            self.model = message.get("model") or self.model
            self.input_tokens = (usage.get("input_tokens") or 0) + (usage.get("cache_read_input_tokens") or 0) + (
                usage.get("cache_creation_input_tokens") or 0)
        elif kind == "content_block_delta":
            delta = event.get("delta") or {}
            if delta.get("type") == "text_delta" and isinstance(delta.get("text"), str):
                self.parts.append(delta["text"])
        elif kind == "message_delta":
            usage = event.get("usage") or {}
            if usage.get("output_tokens") is not None:
                self.output_tokens = usage["output_tokens"]


class AnthropicMessagesAdapter(Adapter):
    protocol = "anthropic.messages"
    provider = "anthropic"

    def segments(self, body: dict) -> list[Segment]:
        out = _content_segments(body.get("system"), "system", body, "system")
        for msg in body.get("messages") or []:
            if not isinstance(msg, dict):
                continue
            role = msg.get("role", "user")
            content = msg.get("content")
            if isinstance(content, str):
                out.append(Segment(content, role, _setter(msg, "content")))
                continue
            for block in content if isinstance(content, list) else []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text" and isinstance(block.get("text"), str):
                    out.append(Segment(block["text"], role, _setter(block, "text")))
                elif block.get("type") == "tool_result":
                    out += _content_segments(block.get("content"), "tool", block)
        return out

    def user_hint(self, body: dict) -> str | None:
        return None  # metadata.user_id is an opaque client identifier, not a directory identity

    def upstream_url(self) -> str:
        return f"{settings.anthropic_base_url}/v1/messages"

    def upstream_headers(self, request: Request) -> dict:
        headers = {"content-type": "application/json", "accept-encoding": "identity",
                   "x-api-key": settings.anthropic_api_key,
                   "anthropic-version": request.headers.get("anthropic-version", "2023-06-01")}
        for name in ("anthropic-beta", "accept"):
            if name in request.headers:
                headers[name] = request.headers[name]
        return headers

    def error(self, status: int, kind: str, message: str, headers: dict | None = None) -> JSONResponse:
        mapped = {"policy_violation": "permission_error"}.get(kind, kind)
        return JSONResponse({"type": "error", "error": {"type": mapped, "message": message}},
                            status_code=status, headers=headers)

    def parse_response(self, data: dict) -> tuple[str, int | None, int | None]:
        text = "".join(b.get("text") or "" for b in data.get("content") or []
                       if isinstance(b, dict) and b.get("type") == "text")
        usage = data.get("usage") or {}
        input_tokens = None
        if usage.get("input_tokens") is not None:
            input_tokens = usage["input_tokens"] + (usage.get("cache_read_input_tokens") or 0) + (
                usage.get("cache_creation_input_tokens") or 0)
        return text, input_tokens, usage.get("output_tokens")

    def stream_parser(self) -> StreamParser:
        return _AnthropicStream()


ADAPTERS: dict[str, Adapter] = {a.protocol: a for a in (
    OpenAIChatAdapter(), OpenAIResponsesAdapter(), AnthropicMessagesAdapter())}
