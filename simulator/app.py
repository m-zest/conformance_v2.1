"""Simulator for local testing and demos.

One small service that stands in for everything outside the gateway:

  /v1/...              a mock model provider speaking the OpenAI chat, OpenAI
                       responses and Anthropic messages protocols. It verifies
                       the gateway's compliance token and rejects direct calls.
  /mock/microsoft/...  a mock Microsoft identity and Graph API serving
                       synthetic Microsoft 365 Copilot interactions.
  /mock/github/...     a mock GitHub API serving Copilot seats and usage reports.
  /hooks/alerts        a webhook sink that shows alert notifications arriving.

Nothing here is used in production. Point the gateway at real endpoints by
changing OPENAI_BASE_URL, ANTHROPIC_BASE_URL and the connector modes.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import re
import time
import uuid
from collections import deque
from datetime import date, datetime, timedelta, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse

from demo import corpus, synth
from sdk.conformance_verifier import ComplianceError, ComplianceVerifier

REQUIRE_TOKEN = os.getenv("REQUIRE_COMPLIANCE_TOKEN", "true").lower() in ("1", "true", "yes")
STREAM_DELAY = float(os.getenv("STREAM_DELAY_SECONDS", "0.02"))
PUBLIC_URL = os.getenv("SIMULATOR_PUBLIC_URL", "http://simulator:9000").rstrip("/")

app = FastAPI(title="Conformance simulator", docs_url=None, redoc_url=None)
verifier = ComplianceVerifier(jwks_url=os.getenv("GATEWAY_JWKS_URL", "http://gateway:8000/.well-known/jwks.json"))
ROSTER = synth.load_roster()
WEBHOOKS: deque = deque(maxlen=100)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


# --------------------------------------------------------------------------- mock model provider

async def _checked_body(request: Request, anthropic: bool = False):
    body = await request.body()
    if REQUIRE_TOKEN:
        try:
            verifier.verify(request.headers.get("x-compliance-token"), body)
        except ComplianceError as exc:
            if anthropic:
                return None, JSONResponse({"type": "error", "error": {"type": "authentication_error",
                                                                      "message": str(exc)}}, status_code=401)
            return None, JSONResponse({"error": {"message": str(exc), "type": "authentication_error",
                                                 "code": "compliance_token_required"}}, status_code=401)
    try:
        return json.loads(body or b"{}"), None
    except ValueError:
        return None, JSONResponse({"error": {"message": "invalid JSON"}}, status_code=400)


def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(p.get("text", "") for p in content if isinstance(p, dict) and isinstance(p.get("text"), str))
    return ""


def _reply(last_user: str) -> str:
    lower = last_user.lower()
    if any(w in lower for w in ("summar", "recap")):
        lead = "Here is a short summary of the main points."
    elif any(w in lower for w in ("draft", "write", "reply", "letter", "email")):
        lead = "Here is a draft you can adapt."
    elif any(w in lower for w in ("code", "function", "script", "sql", "error", "fix")):
        lead = "Here is what I would change and why."
    else:
        lead = "Here is an answer based on what you sent."
    shown = last_user.strip()
    if len(shown) > 600:
        shown = shown[:600] + " ..."
    return (f"{lead}\n\nThis is a simulated model response. The text below is exactly what the model provider "
            f"received from the gateway, so you can see what was masked:\n\n{shown}")


def _chunks(text: str) -> list[str]:
    return re.findall(r"\S+\s*", text) or [text]


def _usage(prompt_chars: int, text: str) -> tuple[int, int]:
    return max(1, prompt_chars // 4), max(1, len(text) // 4)


@app.get("/v1/models")
async def models():
    return {"object": "list", "data": [{"id": m, "object": "model", "owned_by": "simulator"}
                                       for m in ("simulator-small", "simulator-large")]}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body, error = await _checked_body(request)
    if error:
        return error
    messages = body.get("messages") or []
    last_user = next((_text_of(m.get("content")) for m in reversed(messages) if m.get("role") == "user"), "")
    text = _reply(last_user)
    model = body.get("model") or "simulator-small"
    prompt_tokens, completion_tokens = _usage(sum(len(_text_of(m.get("content"))) for m in messages), text)
    usage = {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
             "total_tokens": prompt_tokens + completion_tokens}
    cid, created = f"chatcmpl-{uuid.uuid4().hex[:24]}", int(time.time())
    if not body.get("stream"):
        return {"id": cid, "object": "chat.completion", "created": created, "model": model, "usage": usage,
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": text}}]}

    async def events():
        def chunk(delta: dict, finish=None) -> str:
            return "data: " + json.dumps({"id": cid, "object": "chat.completion.chunk", "created": created,
                                          "model": model, "choices": [{"index": 0, "delta": delta,
                                                                       "finish_reason": finish}]}) + "\n\n"
        yield chunk({"role": "assistant", "content": ""})
        for piece in _chunks(text):
            await asyncio.sleep(STREAM_DELAY)
            yield chunk({"content": piece})
        yield chunk({}, "stop")
        if (body.get("stream_options") or {}).get("include_usage"):
            yield "data: " + json.dumps({"id": cid, "object": "chat.completion.chunk", "created": created,
                                         "model": model, "choices": [], "usage": usage}) + "\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


def _responses_input_text(body: dict) -> tuple[str, int]:
    inp = body.get("input")
    if isinstance(inp, str):
        return inp, len(inp)
    last, total = "", 0
    for item in inp or []:
        if isinstance(item, dict):
            text = _text_of(item.get("content")) or (item.get("output") if isinstance(item.get("output"), str) else "")
            total += len(text)
            if item.get("role") == "user" and text:
                last = text
    return last, total


@app.post("/v1/responses")
async def responses(request: Request):
    body, error = await _checked_body(request)
    if error:
        return error
    last_user, chars = _responses_input_text(body)
    text = _reply(last_user)
    model = body.get("model") or "simulator-small"
    input_tokens, output_tokens = _usage(chars, text)
    rid, mid = f"resp_{uuid.uuid4().hex[:24]}", f"msg_{uuid.uuid4().hex[:24]}"
    final = {"id": rid, "object": "response", "created_at": int(time.time()), "status": "completed", "model": model,
             "output": [{"id": mid, "type": "message", "role": "assistant", "status": "completed",
                         "content": [{"type": "output_text", "text": text, "annotations": []}]}],
             "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens,
                       "total_tokens": input_tokens + output_tokens}}
    if not body.get("stream"):
        return final

    async def events():
        def event(kind: str, data: dict) -> str:
            return f"event: {kind}\ndata: {json.dumps({'type': kind, **data})}\n\n"
        yield event("response.created", {"response": {**final, "status": "in_progress", "output": []}})
        for piece in _chunks(text):
            await asyncio.sleep(STREAM_DELAY)
            yield event("response.output_text.delta", {"item_id": mid, "output_index": 0, "content_index": 0,
                                                       "delta": piece})
        yield event("response.output_text.done", {"item_id": mid, "output_index": 0, "content_index": 0,
                                                  "text": text})
        yield event("response.completed", {"response": final})

    return StreamingResponse(events(), media_type="text/event-stream")


def _anthropic_last_user(body: dict) -> tuple[str, int]:
    total = len(_text_of(body.get("system")))
    last = ""
    for m in body.get("messages") or []:
        text = _text_of(m.get("content"))
        total += len(text)
        if m.get("role") == "user" and text:
            last = text
    return last, total


@app.post("/v1/messages/count_tokens")
async def count_tokens(request: Request):
    body, error = await _checked_body(request, anthropic=True)
    if error:
        return error
    _, chars = _anthropic_last_user(body)
    return {"input_tokens": max(1, chars // 4)}


@app.post("/v1/messages")
async def messages(request: Request):
    body, error = await _checked_body(request, anthropic=True)
    if error:
        return error
    last_user, chars = _anthropic_last_user(body)
    text = _reply(last_user)
    model = body.get("model") or "simulator-large"
    input_tokens, output_tokens = _usage(chars, text)
    mid = f"msg_{uuid.uuid4().hex[:24]}"
    base = {"id": mid, "type": "message", "role": "assistant", "model": model, "stop_sequence": None}
    if not body.get("stream"):
        return {**base, "content": [{"type": "text", "text": text}], "stop_reason": "end_turn",
                "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens}}

    async def events():
        def event(kind: str, data: dict) -> str:
            return f"event: {kind}\ndata: {json.dumps({'type': kind, **data})}\n\n"
        yield event("message_start", {"message": {**base, "content": [], "stop_reason": None,
                                                  "usage": {"input_tokens": input_tokens, "output_tokens": 1}}})
        yield event("content_block_start", {"index": 0, "content_block": {"type": "text", "text": ""}})
        for piece in _chunks(text):
            await asyncio.sleep(STREAM_DELAY)
            yield event("content_block_delta", {"index": 0, "delta": {"type": "text_delta", "text": piece}})
        yield event("content_block_stop", {"index": 0})
        yield event("message_delta", {"delta": {"stop_reason": "end_turn", "stop_sequence": None},
                                      "usage": {"output_tokens": output_tokens}})
        yield event("message_stop", {})

    return StreamingResponse(events(), media_type="text/event-stream")


# --------------------------------------------------------------------------- webhook sink

@app.post("/hooks/alerts")
async def receive_hook(request: Request):
    payload = await request.json()
    WEBHOOKS.appendleft({"received_at": datetime.now(timezone.utc).isoformat(), "payload": payload})
    return {"ok": True}


@app.get("/hooks/alerts")
async def list_hooks():
    return list(WEBHOOKS)


# --------------------------------------------------------------------------- mock Microsoft Graph

APP_CLASSES = {"Word": "IPM.SkypeTeams.Message.Copilot.Word", "Excel": "IPM.SkypeTeams.Message.Copilot.Excel",
               "Outlook": "IPM.SkypeTeams.Message.Copilot.Outlook", "Teams": "IPM.SkypeTeams.Message.Copilot.Teams",
               "PowerPoint": "IPM.SkypeTeams.Message.Copilot.PowerPoint",
               "BizChat": "IPM.SkypeTeams.Message.Copilot.BizChat"}
HOST_WEIGHTS = [("BizChat", 30), ("Outlook", 22), ("Teams", 18), ("Word", 14), ("Excel", 10), ("PowerPoint", 6)]
# Engineering mostly uses coding assistants, so only part of the company holds M365 Copilot licences.
M365_TEAMS = {"Finance", "Human Resources", "Sales", "Legal", "Marketing", "Customer Support"}


def _graph_id(email: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, email))


M365_USERS = [u for u in ROSTER["users"] if u["team"] in M365_TEAMS]
GRAPH_INDEX = {_graph_id(u["email"]): u for u in M365_USERS}


def _stable_rng(*parts) -> random.Random:
    return random.Random(int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:12], 16))


def _m365_day(user: dict, day: date) -> list[dict]:
    rng = _stable_rng("m365", user["email"], day.isoformat())
    weekend = day.weekday() >= 5
    count = max(0, int(rng.gauss(0.4 if weekend else 3.2, 1.6)))
    uid = _graph_id(user["email"])
    items = []
    for n in range(count):
        when = datetime(day.year, day.month, day.day, tzinfo=timezone.utc) + timedelta(
            hours=min(max(rng.gauss(12.5, 2.5), 7.5), 19), seconds=rng.randint(0, 59))
        if rng.random() < 0.07:
            hosts, weights = zip(*[(h, w) for h, _, w in corpus.M365_RISKY])
            host = rng.choices(range(len(hosts)), weights=weights, k=1)[0]
            host, template, _ = corpus.M365_RISKY[host]
            prompt = synth.fill(template, rng)
        else:
            host = rng.choices([h for h, _ in HOST_WEIGHTS], weights=[w for _, w in HOST_WEIGHTS], k=1)[0]
            prompt = rng.choice(corpus.M365_BENIGN[host])
        request_id = str(uuid.uuid5(uuid.NAMESPACE_OID, f"{user['email']}|{day}|{n}"))
        session_id = f"19:{hashlib.sha1(request_id.encode()).hexdigest()[:24]}@thread.v2"
        common = {"sessionId": session_id, "requestId": request_id, "appClass": APP_CLASSES[host],
                  "conversationType": "bizchat" if host == "BizChat" else "appchat", "locale": "en-us",
                  "contexts": [], "attachments": [], "links": [], "mentions": []}
        stamp = when.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        answer = (when + timedelta(seconds=rng.randint(3, 14))).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        items.append({**common, "id": str(int(when.timestamp() * 1000)), "interactionType": "userPrompt",
                      "createdDateTime": stamp, "etag": str(int(when.timestamp() * 1000)),
                      "from": {"@odata.type": "#microsoft.graph.chatMessageFromIdentitySet",
                               "user": {"id": uid, "displayName": user["name"], "userIdentityType": "aadUser"},
                               "application": None, "device": None},
                      "body": {"contentType": "text", "content": prompt}})
        items.append({**common, "id": str(int(when.timestamp() * 1000) + 1), "interactionType": "aiResponse",
                      "createdDateTime": answer, "etag": str(int(when.timestamp() * 1000) + 1),
                      "from": {"@odata.type": "#microsoft.graph.chatMessageFromIdentitySet", "user": None,
                               "application": {"id": "fb8d773d-7ef8-4ec0-a117-179f88add510",
                                               "displayName": f"Copilot in {host}"}, "device": None},
                      "body": {"contentType": "html", "content": f"<p>{rng.choice(corpus.RESPONSES)}</p>"}})
    return items


@app.post("/mock/microsoft/login/{tenant}/oauth2/v2.0/token")
async def ms_token(tenant: str):
    return {"token_type": "Bearer", "expires_in": 3599, "access_token": "simulated-graph-token"}


@app.get("/mock/microsoft/graph/v1.0/users")
async def ms_users():
    return {"@odata.context": "https://graph.microsoft.com/v1.0/$metadata#users", "value": [
        {"id": _graph_id(u["email"]), "displayName": u["name"], "mail": u["email"],
         "userPrincipalName": u["email"], "department": u["team"], "jobTitle": u["title"]} for u in M365_USERS]}


@app.get("/mock/microsoft/graph/v1.0/copilot/users/{user_id}/interactionHistory/getAllEnterpriseInteractions")
async def ms_interactions(user_id: str, request: Request):
    user = GRAPH_INDEX.get(user_id)
    if user is None:
        return JSONResponse({"error": {"code": "NotFound", "message": "User has no Copilot licence"}}, status_code=404)
    params = request.query_params
    now = datetime.now(timezone.utc)
    stamps = re.findall(r"createdDateTime (gt|lt) ([0-9T:.Z-]+)", params.get("$filter", ""))
    since = now - timedelta(days=14)
    until = now
    for op, value in stamps:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        since, until = (parsed, until) if op == "gt" else (since, min(parsed, now))
    items, day = [], since.date()
    while day <= until.date():
        for item in _m365_day(user, day):
            created = datetime.fromisoformat(item["createdDateTime"].replace("Z", "+00:00"))
            if since < created < until:
                items.append(item)
        day += timedelta(days=1)
    top, skip = int(params.get("$top", 100)), int(params.get("$skip", 0))
    page = items[skip:skip + top]
    out = {"@odata.context": "https://graph.microsoft.com/v1.0/$metadata#Collection(microsoft.graph.aiInteraction)",
           "value": page}
    if skip + top < len(items):
        base = str(request.url).split("?")[0].replace(str(request.base_url).rstrip("/"), PUBLIC_URL)
        out["@odata.nextLink"] = f"{base}?$top={top}&$skip={skip + top}&$filter={params.get('$filter', '')}"
    return out


# --------------------------------------------------------------------------- mock GitHub Copilot

GH_USERS = [u for u in ROSTER["users"] if u.get("github")]
IDES = [("vscode", 62), ("jetbrains", 24), ("visualstudio", 8), ("neovim", 6)]
LANGUAGES = [("python", 30), ("typescript", 26), ("sql", 12), ("java", 10), ("go", 9), ("yaml", 7), ("terraform", 6)]
GH_MODELS = [("gpt-4.1", 40), ("claude-sonnet-4.5", 38), ("gemini-2.5-pro", 12), ("gpt-5-mini", 10)]
DORMANT = {"lconti-mrd": 46, "obrandt-mrd": None}   # days since last activity, None means never used


def _gh_day(user: dict, day: date) -> dict | None:
    login = user["github"]
    if login in DORMANT:
        return None
    rng = _stable_rng("github", login, day.isoformat())
    if rng.random() < (0.85 if day.weekday() >= 5 else 0.12):
        return None
    prng = _stable_rng("github-profile", login)
    ide = prng.choices([i for i, _ in IDES], weights=[w for _, w in IDES], k=1)[0]
    language = prng.choices([l for l, _ in LANGUAGES], weights=[w for _, w in LANGUAGES], k=1)[0]
    model = prng.choices([m for m, _ in GH_MODELS], weights=[w for _, w in GH_MODELS], k=1)[0]
    uses_agent = prng.random() < 0.45
    interactions = rng.randint(4, 46)
    generations = rng.randint(30, 260)
    acceptances = int(generations * rng.uniform(0.18, 0.42))
    suggested = generations * rng.randint(2, 6)
    return {
        "report_start_day": day.isoformat(), "report_end_day": day.isoformat(), "day": day.isoformat(),
        "organization_id": "9919", "user_id": 100000 + int(hashlib.sha1(login.encode()).hexdigest()[:5], 16),
        "user_login": login, "user_initiated_interaction_count": interactions,
        "code_generation_activity_count": generations, "code_acceptance_activity_count": acceptances,
        "loc_suggested_to_add_sum": suggested, "loc_added_sum": int(suggested * rng.uniform(0.2, 0.4)),
        "used_chat": True, "used_agent": uses_agent and rng.random() < 0.8,
        "totals_by_ide": [{"ide": ide, "user_initiated_interaction_count": interactions,
                           "code_generation_activity_count": generations}],
        "totals_by_language_feature": [{"language": language, "feature": "code_completion",
                                        "code_generation_activity_count": generations}],
        "totals_by_model_feature": [{"model": model, "feature": "chat_panel_agent_mode" if uses_agent
                                     else "chat_panel_ask_mode", "user_initiated_interaction_count": interactions}],
    }


@app.get("/mock/github/orgs/{org}/copilot/billing/seats")
async def gh_seats(org: str, page: int = 1, per_page: int = 50):
    now = datetime.now(timezone.utc)
    seats = []
    for user in GH_USERS:
        login = user["github"]
        prng = _stable_rng("github-profile", login)
        ide = prng.choices([i for i, _ in IDES], weights=[w for _, w in IDES], k=1)[0]
        if login in DORMANT:
            last = None if DORMANT[login] is None else now - timedelta(days=DORMANT[login])
        else:
            last = now - timedelta(hours=_stable_rng("seat", login, now.date()).randint(1, 40))
        seats.append({"created_at": (now - timedelta(days=prng.randint(60, 300))).isoformat(),
                      "updated_at": now.isoformat(), "pending_cancellation_date": None,
                      "last_activity_at": last.isoformat() if last else None,
                      "last_activity_editor": f"{ide}/1.96.2/copilot-chat/0.23.2" if last else None,
                      "plan_type": "business",
                      "assignee": {"login": login, "id": 100000 + int(hashlib.sha1(login.encode()).hexdigest()[:5], 16),
                                   "type": "User"}})
    start = (page - 1) * per_page
    return {"total_seats": len(seats), "seats": seats[start:start + per_page]}


@app.get("/mock/github/orgs/{org}/copilot/metrics/reports/users-1-day")
async def gh_report(org: str, day: str):
    if date.fromisoformat(day) >= datetime.now(timezone.utc).date():
        return JSONResponse({"message": "Report not available yet"}, status_code=404)
    return {"download_links": [f"{PUBLIC_URL}/mock/github/reports/{org}/users-1-day/{day}.ndjson"], "report_day": day}


@app.get("/mock/github/reports/{org}/users-1-day/{name}")
async def gh_report_file(org: str, name: str):
    day = date.fromisoformat(name.removesuffix(".ndjson"))
    lines = [json.dumps(rec) for rec in (_gh_day(u, day) for u in GH_USERS) if rec]
    return PlainTextResponse("\n".join(lines), media_type="application/x-ndjson")
