"""GitHub Copilot connector.

GitHub does not expose prompt content for Copilot Business or Enterprise, so
this connector provides usage oversight rather than content inspection:
  - seat assignments and last activity (GET /orgs/{org}/copilot/billing/seats)
  - per-user daily usage from the Copilot usage metrics reports, which return
    download links to newline-delimited JSON files

The report path and API version are configurable because GitHub has revised
these endpoints. The field mapping is isolated in parse_usage_record().

Requirements for live mode (see docs/INTEGRATIONS.md): a token for an
organisation owner or a GitHub App with the Copilot Business read permission
and access to Copilot usage metrics.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime, timedelta, timezone

import httpx
from sqlalchemy import delete, select

from ..config import settings
from ..db import SessionLocal, utcnow
from ..gateway.identity import directory
from ..models import Connector, CopilotSeat, CopilotUsageDaily, User

log = logging.getLogger("conformance.connectors.github")
API_VERSION = os.getenv("GITHUB_API_VERSION", "2026-03-10")


def _ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _top(rows, name_key: str, weight_keys: tuple[str, ...]) -> str:
    best, best_weight = "", -1
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        weight = sum(row.get(k) or 0 for k in weight_keys)
        if row.get(name_key) and weight > best_weight:
            best, best_weight = str(row[name_key]), weight
    return best


def parse_usage_record(rec: dict) -> dict | None:
    """Map one line of a per-user usage report to our daily usage columns."""
    login = rec.get("user_login") or rec.get("login")
    day = rec.get("day") or rec.get("report_start_day")
    if not login or not day:
        return None
    weights = ("code_generation_activity_count", "user_initiated_interaction_count")
    return {
        "login": login, "day": date.fromisoformat(day[:10]),
        "interactions": int(rec.get("user_initiated_interaction_count") or 0),
        "code_generations": int(rec.get("code_generation_activity_count") or 0),
        "code_acceptances": int(rec.get("code_acceptance_activity_count") or 0),
        "loc_suggested": int(rec.get("loc_suggested_to_add_sum") or 0),
        "loc_accepted": int(rec.get("loc_added_sum") or 0),
        "used_chat": bool(rec.get("used_chat")), "used_agent": bool(rec.get("used_agent")),
        "top_ide": _top(rec.get("totals_by_ide"), "ide", weights),
        "top_language": _top(rec.get("totals_by_language_feature"), "language", weights),
        "top_model": _top(rec.get("totals_by_model_feature") or rec.get("totals_by_language_model"), "model", weights),
    }


class GitHubCopilotConnector:
    id = "github-copilot"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def sync(self, connector: Connector) -> int:
        base = f"{settings.simulator_url}/mock/github" if connector.mode == "demo" else settings.github_api_url
        headers = {"Authorization": f"Bearer {settings.github_token}", "Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": API_VERSION}
        client = self._client or httpx.AsyncClient(timeout=60, follow_redirects=True)
        try:
            seats = await self._seats(client, base, headers)
            logins = await self._user_map(seats)
            await self._store_seats(seats, logins)
            cursor = dict(connector.cursor or {})
            today = utcnow().date()
            last = date.fromisoformat(cursor["last_day"]) if cursor.get("last_day") else (
                today - timedelta(days=settings.github_lookback_days + 1))
            stored = len(seats)
            day = last + timedelta(days=1)
            while day < today:   # reports cover complete days
                records = await self._usage(client, base, headers, day)
                if records is None:
                    break   # report not published yet, try again on the next sync
                stored += await self._store_usage(records, logins)
                cursor["last_day"] = day.isoformat()
                day += timedelta(days=1)
            connector.cursor = cursor
            return stored
        finally:
            if self._client is None:
                await client.aclose()

    async def _seats(self, client: httpx.AsyncClient, base: str, headers: dict) -> list[dict]:
        seats, page = [], 1
        while True:
            resp = await client.get(f"{base}/orgs/{settings.github_org}/copilot/billing/seats", headers=headers,
                                    params={"per_page": 100, "page": page})
            resp.raise_for_status()
            batch = resp.json().get("seats", [])
            seats += batch
            if len(batch) < 100:
                return seats
            page += 1

    async def _usage(self, client: httpx.AsyncClient, base: str, headers: dict, day: date) -> list[dict] | None:
        path = settings.github_usage_report_path.format(org=settings.github_org)
        resp = await client.get(f"{base}{path}", headers=headers, params={"day": day.isoformat()})
        if resp.status_code in (204, 404):
            return None
        resp.raise_for_status()
        records: list[dict] = []
        for link in resp.json().get("download_links", []):
            file = await client.get(link)
            file.raise_for_status()
            for line in file.text.splitlines():
                if line.strip():
                    parsed = parse_usage_record(json.loads(line))
                    if parsed:
                        records.append(parsed)
        return records

    async def _user_map(self, seats: list[dict]) -> dict[str, str]:
        logins = [s.get("assignee", {}).get("login") for s in seats if s.get("assignee")]
        async with SessionLocal() as session:
            known = {u.github_login: u.id for u in (await session.execute(
                select(User).where(User.github_login.in_(logins)))).scalars()}
        for seat in seats:
            assignee = seat.get("assignee") or {}
            login = assignee.get("login")
            if login and login not in known:
                email = assignee.get("email")
                ref = await directory.ensure_user(email or f"github:{login}", email=email, name=assignee.get("name"),
                                                  source="connector", github_login=login)
                known[login] = ref.id
        return known

    async def _store_seats(self, seats: list[dict], logins: dict[str, str]) -> None:
        async with SessionLocal() as session:
            await session.execute(delete(CopilotSeat).where(CopilotSeat.connector_id == self.id))
            for seat in seats:
                login = (seat.get("assignee") or {}).get("login")
                if not login:
                    continue
                session.add(CopilotSeat(connector_id=self.id, login=login, user_id=logins.get(login),
                                        plan=seat.get("plan_type") or "", assigned_at=_ts(seat.get("created_at")),
                                        last_activity_at=_ts(seat.get("last_activity_at")),
                                        last_activity_editor=(seat.get("last_activity_editor") or "")[:160]))
            await session.commit()

    async def _store_usage(self, records: list[dict], logins: dict[str, str]) -> int:
        if not records:
            return 0
        days = {r["day"] for r in records}
        async with SessionLocal() as session:
            await session.execute(delete(CopilotUsageDaily).where(
                CopilotUsageDaily.connector_id == self.id, CopilotUsageDaily.day.in_(days)))
            for r in records:
                session.add(CopilotUsageDaily(connector_id=self.id, user_id=logins.get(r["login"]), **r))
            await session.commit()
        return len(records)
