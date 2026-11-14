"""Alert notifications: Slack, Microsoft Teams, generic webhook and email.

Notifications never contain the sensitive value or the prompt. They carry the
alert title, severity, user, tool and a link to the dashboard.
"""
from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

import httpx

from .config import settings
from .db import SessionLocal
from .detection.model import SEVERITY
from .models import Notification

log = logging.getLogger("conformance.notifications")


def channels() -> list[dict]:
    return [
        {"id": "slack", "name": "Slack", "configured": bool(settings.slack_webhook_url)},
        {"id": "teams", "name": "Microsoft Teams", "configured": bool(settings.teams_webhook_url)},
        {"id": "webhook", "name": "Webhook (SIEM, ticketing)", "configured": bool(settings.alert_webhook_url)},
        {"id": "email", "name": "Email (SMTP)", "configured": bool(settings.smtp_host and settings.smtp_to)},
    ]


def _link(alert: dict) -> str:
    return f"{settings.dashboard_url}/alerts/{alert['id']}"


def _text(alert: dict) -> str:
    return (f"[{alert['severity'].upper()}] {alert['title']}\n{alert['summary']}\n"
            f"User: {alert['user'] or 'unknown'} | Tool: {alert['tool'] or 'unknown'}\n{_link(alert)}")


async def _post(client: httpx.AsyncClient, url: str, payload: dict) -> str:
    resp = await client.post(url, json=payload)
    resp.raise_for_status()
    return f"HTTP {resp.status_code}"


def _send_email(alert: dict) -> str:
    msg = EmailMessage()
    msg["Subject"] = f"[Conformance] {alert['severity'].upper()}: {alert['title']}"
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = ", ".join(settings.smtp_to)
    msg.set_content(_text(alert))
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)
    return f"sent to {len(settings.smtp_to)} recipient(s)"


async def send(alert: dict, only: str | None = None) -> list[dict]:
    """Deliver one alert to every configured channel and record the outcome."""
    results: list[dict] = []
    jobs: list[tuple[str, object]] = []
    async with httpx.AsyncClient(timeout=10) as client:
        if settings.slack_webhook_url and only in (None, "slack"):
            jobs.append(("slack", _post(client, settings.slack_webhook_url, {"text": _text(alert)})))
        if settings.teams_webhook_url and only in (None, "teams"):
            card = {"type": "message", "attachments": [{
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {"$schema": "http://adaptivecards.io/schemas/adaptive-card.json", "type": "AdaptiveCard",
                            "version": "1.4", "body": [
                                {"type": "TextBlock", "weight": "Bolder", "size": "Medium", "wrap": True,
                                 "text": f"{alert['severity'].upper()}: {alert['title']}"},
                                {"type": "TextBlock", "wrap": True, "text": alert["summary"]},
                                {"type": "FactSet", "facts": [{"title": "User", "value": alert["user"] or "unknown"},
                                                              {"title": "Tool", "value": alert["tool"] or "unknown"}]}],
                            "actions": [{"type": "Action.OpenUrl", "title": "Open alert", "url": _link(alert)}]}}]}
            jobs.append(("teams", _post(client, settings.teams_webhook_url, card)))
        if settings.alert_webhook_url and only in (None, "webhook"):
            jobs.append(("webhook", _post(client, settings.alert_webhook_url,
                                          {"event": "alert.created", "alert": {**alert, "url": _link(alert)}})))
        if settings.smtp_host and settings.smtp_to and only in (None, "email"):
            jobs.append(("email", asyncio.to_thread(_send_email, alert)))
        outcomes = await asyncio.gather(*(job for _, job in jobs), return_exceptions=True)
    for (channel, _), outcome in zip(jobs, outcomes):
        failed = isinstance(outcome, Exception)
        results.append({"channel": channel, "status": "failed" if failed else "sent",
                        "detail": f"{type(outcome).__name__}: {outcome}"[:300] if failed else str(outcome)})
    if results:
        try:
            async with SessionLocal() as session:
                for r in results:
                    session.add(Notification(channel=r["channel"], alert_id=alert.get("id"),
                                             subject=alert["title"][:255], status=r["status"], detail=r["detail"]))
                await session.commit()
        except Exception:
            log.exception("could not record notification results")
    return results


async def dispatch(alerts: list[dict]) -> None:
    minimum = SEVERITY.get(settings.notify_min_severity, 3)
    for alert in alerts:
        if SEVERITY.get(alert["severity"], 0) >= minimum:
            try:
                await send(alert)
            except Exception:
                log.exception("notification dispatch failed")
