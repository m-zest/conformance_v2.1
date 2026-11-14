"""Microsoft 365 Copilot connector.

Microsoft 365 Copilot cannot be routed through a gateway, so it is observed
after the fact. This connector reads prompts and responses from the Microsoft
Graph AI interaction export and runs them through the same detectors as
gateway traffic. Findings raise the same alerts, but nothing can be blocked.

Requirements for live mode (see docs/INTEGRATIONS.md):
  - an Entra app registration with the application permissions
    AiEnterpriseInteraction.Read.All and User.Read.All, admin consented
  - Microsoft 365 Copilot licences on the users to be monitored

In demo mode the same code runs against the bundled simulator.
"""
from __future__ import annotations

import html
import logging
import re
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select

from ..config import settings
from ..db import SessionLocal, utcnow
from ..detection.engine import Segment, engine
from ..gateway.identity import directory
from ..models import Connector, RequestLog
from ..policy import PolicyView, apply_policy, policies
from ..recorder import Record, recorder

log = logging.getLogger("conformance.connectors.m365")

HOST_APPS = {"bizchat": "Copilot Chat", "webchat": "Copilot Chat", "teams": "Teams", "word": "Word",
             "excel": "Excel", "powerpoint": "PowerPoint", "outlook": "Outlook", "onenote": "OneNote",
             "loop": "Loop", "whiteboard": "Whiteboard", "sharepoint": "SharePoint", "forms": "Forms",
             "planner": "Planner", "designer": "Designer"}
_TAGS = re.compile(r"<[^>]+>")


def host_app(app_class: str | None) -> str:
    tail = (app_class or "").rsplit(".", 1)[-1].lower()
    return HOST_APPS.get(tail, tail.title() or "Copilot")


def plain_text(body: dict | None) -> str:
    if not body:
        return ""
    content = body.get("content") or ""
    if (body.get("contentType") or "").lower() == "html":
        content = html.unescape(_TAGS.sub(" ", content))
    return content.strip()


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _odata_ts(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class M365CopilotConnector:
    id = "m365-copilot"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    def _urls(self, mode: str) -> tuple[str, str]:
        if mode == "demo":
            return (f"{settings.simulator_url}/mock/microsoft/login", f"{settings.simulator_url}/mock/microsoft/graph")
        return settings.m365_login_url, settings.m365_graph_url

    async def _token(self, client: httpx.AsyncClient, login_url: str) -> str:
        resp = await client.post(f"{login_url}/{settings.m365_tenant_id}/oauth2/v2.0/token", data={
            "grant_type": "client_credentials", "client_id": settings.m365_client_id,
            "client_secret": settings.m365_client_secret, "scope": "https://graph.microsoft.com/.default"})
        resp.raise_for_status()
        return resp.json()["access_token"]

    async def _paged(self, client: httpx.AsyncClient, url: str, headers: dict, params: dict | None = None):
        while url:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code in (403, 404):
                return
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("value", []):
                yield item
            url, params = data.get("@odata.nextLink"), None

    async def sync(self, connector: Connector) -> int:
        login_url, graph_url = self._urls(connector.mode)
        client = self._client or httpx.AsyncClient(timeout=60)
        until = utcnow()
        last = (connector.cursor or {}).get("until")
        since = _parse_ts(last) - timedelta(minutes=5) if last else until - timedelta(days=settings.m365_lookback_days)
        default_policy = await policies.for_app(None)
        policy = PolicyView(default_policy.id, default_policy.name, "monitor", default_policy.rules,
                            default_policy.custom_terms, default_policy.version)
        stored = 0
        try:
            token = await self._token(client, login_url)
            headers = {"Authorization": f"Bearer {token}"}
            users = [u async for u in self._paged(client, f"{graph_url}/v1.0/users", headers, {
                "$select": "id,displayName,mail,userPrincipalName,department,jobTitle", "$top": "999"})]
            for user in users:
                email = (user.get("mail") or user.get("userPrincipalName") or "").lower()
                if not email:
                    continue
                url = f"{graph_url}/v1.0/copilot/users/{user['id']}/interactionHistory/getAllEnterpriseInteractions"
                params = {"$top": "100", "$filter": f"createdDateTime gt {_odata_ts(since)} and "
                                                    f"createdDateTime lt {_odata_ts(until)}"}
                pairs: dict[str, dict] = {}
                async for item in self._paged(client, url, headers, params):
                    key = item.get("requestId") or item.get("id")
                    slot = pairs.setdefault(key, {})
                    slot["response" if item.get("interactionType") == "aiResponse" else "prompt"] = item
                if not pairs:
                    continue
                ref = await directory.ensure_user(email, email=email, name=user.get("displayName"),
                                                  team=user.get("department"), title=user.get("jobTitle"),
                                                  source="connector")
                stored += await self._store(pairs, user["id"], ref, policy)
        finally:
            if self._client is None:
                await client.aclose()
        connector.cursor = {"until": _odata_ts(until)}
        return stored

    async def _store(self, pairs: dict[str, dict], graph_user_id: str, ref, policy: PolicyView) -> int:
        ids = {key: f"m365:{graph_user_id}:{key}" for key in pairs}
        async with SessionLocal() as session:
            known = set((await session.execute(select(RequestLog.external_id).where(
                RequestLog.external_id.in_(list(ids.values()))))).scalars())
        count = 0
        for key, pair in sorted(pairs.items(), key=lambda kv: (kv[1].get("prompt") or kv[1].get("response") or {}).get(
                "createdDateTime", "")):
            prompt = pair.get("prompt")
            if prompt is None or ids[key] in known:
                continue
            text = plain_text(prompt.get("body"))
            if not text:
                continue
            segments = [Segment(text, "user")]
            detected, _ = await engine.scan_segments(segments, policy.custom_terms)
            findings, _ = apply_policy(policy, detected)
            for f in findings:
                f.action = "log"
            response = pair.get("response") or {}
            created = _parse_ts(prompt["createdDateTime"])
            await recorder.persist(Record(
                user_id=ref.id, user_label=ref.label, app_id=self.id, app_name="Microsoft 365 Copilot", policy=policy,
                ts=created, source="m365_copilot", external_id=ids[key],
                protocol="connector", provider="microsoft", host_app=host_app(prompt.get("appClass")),
                action="observed", segments=segments, findings=findings,
                response_text=plain_text(response.get("body"))),
                notify=utcnow() - created < timedelta(hours=24))   # no notification flood for imported history
            count += 1
        return count
