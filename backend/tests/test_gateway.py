import json
import random

import jwt
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Alert, Finding, RequestLog, User
from app.signing import body_hash, signer
from conftest import TEST_KEY, settle, user_headers
from demo import synth
from sdk.conformance_verifier import ComplianceError, ComplianceVerifier

CARD = "4539 1488 0343 6467"


async def last_request(user_email):
    await settle()
    async with SessionLocal() as s:
        user = (await s.execute(select(User).where(User.external_id == user_email))).scalar_one()
        row = (await s.execute(select(RequestLog).where(RequestLog.user_id == user.id)
                               .order_by(RequestLog.ts.desc()))).scalars().first()
        findings = (await s.execute(select(Finding).where(Finding.request_id == row.id))).scalars().all()
        return row, findings


def chat(text, **extra):
    return {"model": "simulator-small", "messages": [{"role": "user", "content": text}], **extra}


async def test_requires_a_gateway_key(client):
    assert (await client.post("/v1/chat/completions", json=chat("hi"))).status_code == 401
    resp = await client.post("/v1/chat/completions", json=chat("hi"), headers={"Authorization": "Bearer gw_wrong"})
    assert resp.status_code == 401 and resp.json()["error"]["type"] == "authentication_error"
    resp = await client.post("/v1/messages", json={}, headers={"x-api-key": "gw_wrong"})
    assert resp.json()["type"] == "error"


async def test_clean_request_is_forwarded_and_recorded(client):
    headers = user_headers("clean.user@meridian.example", "Clean User", "Legal")
    resp = await client.post("/v1/chat/completions", json=chat("Explain IFRS 16 briefly."), headers=headers)
    assert resp.status_code == 200
    assert resp.headers["x-conformance-action"] == "allowed"
    assert "Explain IFRS 16 briefly." in resp.json()["choices"][0]["message"]["content"]
    row, findings = await last_request("clean.user@meridian.example")
    assert row.action == "allowed" and row.finding_count == 0 and not findings
    assert row.input_tokens > 0 and row.output_tokens > 0 and not row.usage_estimated
    assert row.token_jti == row.id


async def test_pii_is_masked_before_it_reaches_the_provider(client):
    headers = user_headers("mask.user@meridian.example", "Mask User", "Finance")
    text = f"Refund card {CARD} to IBAN DE89 3704 0044 0532 0130 00 and email mario.rossi@mailbox.example"
    resp = await client.post("/v1/chat/completions", json=chat(text), headers=headers)
    assert resp.status_code == 200 and resp.headers["x-conformance-action"] == "masked"
    seen_by_model = resp.json()["choices"][0]["message"]["content"]
    assert CARD not in seen_by_model and "DE89" not in seen_by_model
    assert "[CREDIT_CARD_1]" in seen_by_model and "[IBAN_1]" in seen_by_model
    assert "mario.rossi@mailbox.example" in seen_by_model   # contact details are logged, not masked, by default
    row, findings = await last_request("mask.user@meridian.example")
    assert row.action == "masked" and {f.entity_type for f in findings} == {"CREDIT_CARD", "IBAN", "EMAIL_ADDRESS"}
    assert CARD not in row.prompt_text and "mario.rossi" not in row.prompt_text   # stored copy is fully redacted
    assert all(CARD.replace(" ", "") not in f.preview for f in findings)


async def test_credentials_are_blocked(client):
    headers = user_headers("block.user@meridian.example", "Block User", "Engineering")
    secret = synth.aws_access_key(random.Random(1))
    resp = await client.post("/v1/chat/completions", json=chat(f"Why does this fail? AWS_ACCESS_KEY_ID={secret}"),
                             headers=headers)
    assert resp.status_code == 403 and resp.headers["x-conformance-action"] == "blocked"
    assert "AWS access key" in resp.json()["error"]["message"]
    row, findings = await last_request("block.user@meridian.example")
    assert row.action == "blocked" and row.upstream_status is None and secret not in (row.prompt_text or "")
    async with SessionLocal() as s:
        alert = (await s.execute(select(Alert).where(Alert.request_id == row.id))).scalars().first()
    assert alert is not None and alert.rule_id == "credential-exposure" and alert.severity == 4


async def test_streaming_chat(client):
    headers = user_headers("stream.user@meridian.example", "Stream User", "Sales")
    resp = await client.post("/v1/chat/completions", headers=headers,
                             json=chat(f"Card {CARD} please", stream=True, stream_options={"include_usage": True}))
    assert resp.status_code == 200 and resp.headers["content-type"].startswith("text/event-stream")
    assert "data: [DONE]" in resp.text and CARD not in resp.text
    row, _ = await last_request("stream.user@meridian.example")
    assert row.stream and row.action == "masked" and "[CREDIT_CARD_1]" in row.response_text
    assert not row.usage_estimated and row.output_tokens > 0


async def test_anthropic_messages_protocol(client):
    headers = {"x-api-key": TEST_KEY, "anthropic-version": "2023-06-01",
               "X-End-User": "claude.user@meridian.example"}
    body = {"model": "claude-sonnet-4-5", "max_tokens": 200, "system": [{"type": "text", "text": "Be brief."}],
            "messages": [{"role": "user", "content": [{"type": "text", "text": "My SSN is 123-45-6789"}]},
                         {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "read", "input": {}}]},
                         {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1",
                                                       "content": [{"type": "text", "text": f"file has card {CARD}"}]}]}]}
    resp = await client.post("/v1/messages", json=body, headers=headers)
    assert resp.status_code == 200 and resp.json()["type"] == "message"
    row, findings = await last_request("claude.user@meridian.example")
    assert row.protocol == "anthropic.messages" and {f.entity_type for f in findings} == {"US_SSN", "CREDIT_CARD"}
    assert "[tool result]" in row.prompt_text and CARD not in row.prompt_text

    resp = await client.post("/v1/messages", json={**body, "stream": True}, headers=headers)
    assert "event: message_stop" in resp.text
    row, findings = await last_request("claude.user@meridian.example")
    assert row.stream and row.output_tokens > 0
    assert all(not f.is_new for f in findings)   # same values again: recorded as repeats, not new exposure

    resp = await client.post("/v1/messages/count_tokens", json=body, headers=headers)
    assert resp.status_code == 200 and resp.json()["input_tokens"] > 0


async def test_responses_protocol(client):
    headers = user_headers("codex.user@meridian.example", "Codex User", "Engineering")
    body = {"model": "simulator-small", "instructions": "You are a coding agent.",
            "input": [{"role": "user", "content": [{"type": "input_text", "text": f"pay with {CARD}"}]},
                      {"type": "function_call_output", "call_id": "c1", "output": "IBAN DE89 3704 0044 0532 0130 00"}]}
    resp = await client.post("/v1/responses", json=body, headers=headers)
    assert resp.status_code == 200 and resp.json()["object"] == "response"
    row, findings = await last_request("codex.user@meridian.example")
    assert {f.entity_type for f in findings} == {"CREDIT_CARD", "IBAN"} and row.action == "masked"
    resp = await client.post("/v1/responses", json={**body, "stream": True}, headers=headers)
    assert "response.completed" in resp.text


async def test_repeated_history_does_not_raise_new_alerts(client):
    headers = user_headers("history.user@meridian.example", "History User", "Finance")
    first = [{"role": "user", "content": f"Card {CARD}"}]
    await client.post("/v1/chat/completions", json={"model": "m", "messages": first}, headers=headers)
    row1, f1 = await last_request("history.user@meridian.example")
    follow = first + [{"role": "assistant", "content": "Noted."}, {"role": "user", "content": "Thanks, anything else?"}]
    await client.post("/v1/chat/completions", json={"model": "m", "messages": follow}, headers=headers)
    row2, f2 = await last_request("history.user@meridian.example")
    assert row1.new_finding_count == 1 and row2.new_finding_count == 0 and row2.finding_count == 1
    assert row2.action == "masked"   # history is still masked on the way out
    async with SessionLocal() as s:
        alerts = (await s.execute(select(Alert).where(Alert.user_id == row1.user_id))).scalars().all()
    assert len(alerts) == 1 and alerts[0].occurrences == 1


async def test_compliance_token_binds_the_forwarded_body(client, stack):
    captured = {}
    original = stack["sim"].verifier.verify

    def spy(token, body):
        captured.update(token=token, body=body)
        return original(token, body)

    stack["sim"].verifier.verify = spy
    try:
        resp = await client.post("/v1/chat/completions", json=chat(f"card {CARD}"),
                                 headers=user_headers("token.user@meridian.example"))
    finally:
        stack["sim"].verifier.verify = original
    assert resp.status_code == 200
    claims = jwt.decode(captured["token"], options={"verify_signature": False})
    assert claims["dec"] == "masked" and claims["bh"] == body_hash(captured["body"])
    assert CARD not in captured["body"].decode() and claims["pol"]["mode"] == "enforce"
    verifier = ComplianceVerifier(jwks=signer.jwks())
    assert verifier.verify(captured["token"], captured["body"])["jti"] == claims["jti"]
    for tampered in (captured["body"] + b" ", json.dumps(chat(f"card {CARD}")).encode()):
        try:
            verifier.verify(captured["token"], tampered)
            raise AssertionError("tampered body was accepted")
        except ComplianceError:
            pass


async def test_provider_rejects_requests_that_bypass_the_gateway(stack):
    resp = await stack["upstream"].post("/v1/chat/completions", json=chat("hello"))
    assert resp.status_code == 401 and resp.json()["error"]["code"] == "compliance_token_required"


async def test_invalid_bodies(client):
    headers = user_headers()
    assert (await client.post("/v1/chat/completions", content=b"not json", headers=headers)).status_code == 400
    assert (await client.post("/v1/chat/completions", content=b"[1,2]", headers=headers)).status_code == 400
