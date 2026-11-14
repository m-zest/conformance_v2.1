"""Conformance AI Gateway: application entry point."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import delete, text

from . import bootstrap
from .api import admin, auth, copilot, insights
from .config import VERSION, settings
from .connectors.scheduler import scheduler
from .db import SessionLocal, engine as db_engine, init_models, utcnow
from .detection.engine import engine as detection
from .gateway.identity import directory
from .gateway.proxy import gateway
from .gateway.routes import router as gateway_router
from .models import Finding, Notification, RequestLog, SeenFingerprint
from .recorder import recorder

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("conformance")


async def _maintenance() -> None:
    """Hourly housekeeping: retention and key usage timestamps."""
    while True:
        try:
            await directory.flush_key_usage()
            cutoff = utcnow() - timedelta(days=settings.retention_days)
            async with SessionLocal() as session:
                old = delete(Finding).where(Finding.ts < cutoff)
                await session.execute(old)
                result = await session.execute(delete(RequestLog).where(RequestLog.ts < cutoff))
                await session.execute(delete(SeenFingerprint).where(SeenFingerprint.last_seen < cutoff))
                await session.execute(delete(Notification).where(Notification.ts < cutoff))
                await session.commit()
                if result.rowcount:
                    log.info("retention removed %d interaction records older than %d days", result.rowcount,
                             settings.retention_days)
        except Exception:
            log.exception("maintenance task failed")
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_models()
    await bootstrap.run()
    recorder.start()
    if settings.demo_mode and settings.demo_seed:
        from .demo.seed import seed_if_empty, work_the_inbox
        if await seed_if_empty():
            for connector_id in scheduler.connectors:   # first import of the simulated vendor history
                await scheduler.sync(connector_id)
            await work_the_inbox()
    scheduler.start()
    maintenance = asyncio.create_task(_maintenance(), name="maintenance")
    if settings.using_default_admin_password:
        log.warning("The dashboard admin account uses the default password. Set ADMIN_PASSWORD before sharing access.")
    log.info("Conformance gateway %s ready", VERSION)
    yield
    maintenance.cancel()
    await scheduler.stop()
    await recorder.stop()
    await gateway.close()
    await detection.guard.close()
    await db_engine.dispose()


app = FastAPI(title="Conformance AI Gateway", version=VERSION, lifespan=lifespan,
              docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)
app.include_router(gateway_router)
app.include_router(auth.router)
app.include_router(insights.router)
app.include_router(admin.router)
app.include_router(copilot.router)


@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"status": "ok", "version": VERSION}


@app.get("/readyz", include_in_schema=False)
async def readyz():
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse({"status": "database unavailable"}, status_code=503)
    return {"status": "ready"}


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse({"detail": "Internal error"}, status_code=500)
