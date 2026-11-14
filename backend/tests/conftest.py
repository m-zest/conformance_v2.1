"""Test harness: the gateway and the simulator run in-process, wired together over ASGI."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]

TEST_KEY = "gw_test_key_for_the_internal_assistant"
os.environ.update({
    "DATA_DIR": tempfile.mkdtemp(prefix="conformance-test-"), "DATABASE_URL": "", "SECRET_KEY": "test-secret-key-that-is-long-enough-for-hs256",
    "DEMO_MODE": "true", "DEMO_SEED": "false", "DEMO_APP_KEY": TEST_KEY, "NER_ENABLED": "false",
    "OPENAI_BASE_URL": "http://simulator/v1", "ANTHROPIC_BASE_URL": "http://simulator",
    "SIMULATOR_URL": "http://simulator", "SIMULATOR_PUBLIC_URL": "http://simulator",
    "M365_COPILOT_MODE": "demo", "GITHUB_COPILOT_MODE": "demo", "STREAM_DELAY_SECONDS": "0",
    "REQUIRE_COMPLIANCE_TOKEN": "true", "ADMIN_PASSWORD": "test-admin-password",
    "ALERT_WEBHOOK_URL": "", "SLACK_WEBHOOK_URL": "", "TEAMS_WEBHOOK_URL": "", "SMTP_HOST": "",
})

import httpx  # noqa: E402
import pytest_asyncio  # noqa: E402


@pytest_asyncio.fixture(scope="session")
async def stack():
    import simulator.app as sim
    from app.connectors.scheduler import scheduler
    from app.gateway.proxy import gateway
    from app.main import app
    from app.signing import signer
    from sdk.conformance_verifier import ComplianceVerifier

    sim.verifier = ComplianceVerifier(jwks=signer.jwks())
    upstream = httpx.AsyncClient(transport=httpx.ASGITransport(app=sim.app), base_url="http://simulator")
    gateway.client = upstream
    for connector in scheduler.connectors.values():
        connector._client = upstream
    scheduler.start = lambda: None   # connectors are driven explicitly in tests
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://gateway") as client:
            yield {"client": client, "upstream": upstream, "sim": sim}
    await upstream.aclose()


@pytest_asyncio.fixture(scope="session")
async def client(stack):
    return stack["client"]


@pytest_asyncio.fixture(scope="session")
async def admin(client):
    resp = await client.post("/api/auth/login", json={"email": "admin@meridian.example",
                                                      "password": "test-admin-password"})
    assert resp.status_code == 200, resp.text
    return client


def user_headers(email="elena.marchetti@meridian.example", name="Elena Marchetti", team="Finance"):
    return {"Authorization": f"Bearer {TEST_KEY}", "X-End-User": email, "X-End-User-Name": name,
            "X-End-User-Team": team}


async def settle():
    from app.recorder import recorder
    await recorder.flush()
