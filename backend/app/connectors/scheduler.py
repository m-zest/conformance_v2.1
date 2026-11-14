"""Runs the connectors on an interval and records their status."""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from ..config import settings
from ..db import SessionLocal, utcnow
from ..models import Connector
from .github_copilot import GitHubCopilotConnector
from .m365_copilot import M365CopilotConnector

log = logging.getLogger("conformance.connectors")


class ConnectorScheduler:
    def __init__(self) -> None:
        self.connectors = {c.id: c for c in (M365CopilotConnector(), GitHubCopilotConnector())}
        self._task: asyncio.Task | None = None
        self._locks: dict[str, asyncio.Lock] = {cid: asyncio.Lock() for cid in self.connectors}

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop(), name="connectors")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()

    async def _loop(self) -> None:
        await asyncio.sleep(3)
        while True:
            for connector_id in self.connectors:
                try:
                    await self.sync(connector_id)
                except Exception:
                    log.exception("connector %s crashed", connector_id)
            await asyncio.sleep(settings.connector_poll_seconds)

    async def sync(self, connector_id: str) -> dict:
        impl = self.connectors[connector_id]
        async with self._locks[connector_id]:
            async with SessionLocal() as session:
                row = (await session.execute(select(Connector).where(Connector.id == connector_id))).scalar_one_or_none()
                if row is None or row.mode == "disabled":
                    return {"status": "disabled"}
                try:
                    count = await impl.sync(row)
                    row.last_status, row.last_error = "ok", ""
                    row.items_synced = (row.items_synced or 0) + count
                    log.info("connector %s synced %d item(s)", connector_id, count)
                except Exception as exc:
                    row.last_status = "error"
                    row.last_error = f"{type(exc).__name__}: {exc}"[:500]
                    log.warning("connector %s failed: %s", connector_id, row.last_error)
                row.last_sync_at = utcnow()
                await session.commit()
                return {"status": row.last_status, "error": row.last_error}


scheduler = ConnectorScheduler()
