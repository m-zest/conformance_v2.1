"""Sample internal tool: a small company chat assistant.

It shows the integration pattern for an internal web application:

  1. The browser never talks to the model provider or to the gateway directly.
  2. This backend holds one gateway application key (GATEWAY_KEY).
  3. On every call it tells the gateway which signed-in employee is asking,
     using the X-End-User headers. The gateway trusts that assertion because
     the application is registered as trusted.

The "signed in as" selector stands in for your single sign-on. In a real tool
the identity comes from the session, not from a field the user can change.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from demo import synth

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://gateway:8000").rstrip("/")
GATEWAY_KEY = os.getenv("GATEWAY_KEY", "")
MODEL = os.getenv("MODEL", "simulator-small")
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:8080")
STATIC = Path(__file__).parent / "static"

app = FastAPI(title="Internal Assistant (sample tool)", docs_url=None, redoc_url=None)
ROSTER = {u["email"]: u for u in synth.load_roster()["users"]}
client = httpx.AsyncClient(timeout=httpx.Timeout(120, connect=10))


class ChatBody(BaseModel):
    user: str
    messages: list[dict]


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/api/config")
async def config():
    users = [{"email": u["email"], "name": u["name"], "team": u["team"], "title": u["title"]} for u in ROSTER.values()]
    return {"users": users, "dashboard_url": DASHBOARD_URL, "model": MODEL}


def _event(kind: str, data: dict) -> str:
    return f"event: {kind}\ndata: {json.dumps(data)}\n\n"


@app.post("/api/chat")
async def chat(body: ChatBody, request: Request):
    user = ROSTER.get(body.user)
    if user is None:
        raise HTTPException(400, "Unknown user")
    headers = {
        "Authorization": f"Bearer {GATEWAY_KEY}",
        "X-End-User": user["email"], "X-End-User-Name": user["name"], "X-End-User-Team": user["team"],
    }
    payload = {"model": MODEL, "stream": True, "messages": body.messages}

    async def relay():
        try:
            async with client.stream("POST", f"{GATEWAY_URL}/v1/chat/completions", json=payload, headers=headers) as resp:
                meta = {"action": resp.headers.get("x-conformance-action", ""),
                        "findings": int(resp.headers.get("x-conformance-findings", "0") or 0),
                        "request_id": resp.headers.get("x-conformance-request-id", ""),
                        "mode": resp.headers.get("x-conformance-policy-mode", "")}
                if resp.status_code != 200:
                    raw = await resp.aread()
                    try:
                        message = json.loads(raw)["error"]["message"]
                    except Exception:
                        message = f"The gateway returned HTTP {resp.status_code}."
                    yield _event("blocked" if resp.status_code == 403 else "error", {**meta, "message": message})
                    return
                yield _event("meta", meta)
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        delta = json.loads(data)["choices"][0]["delta"].get("content")
                    except (ValueError, KeyError, IndexError):
                        continue
                    if delta:
                        yield _event("delta", {"text": delta})
                yield _event("done", {})
        except httpx.HTTPError as exc:
            yield _event("error", {"message": f"The gateway is not reachable: {type(exc).__name__}"})

    return StreamingResponse(relay(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
