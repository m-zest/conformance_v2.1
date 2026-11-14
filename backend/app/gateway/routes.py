"""Gateway endpoints. These are the URLs that AI tools are pointed at."""
from __future__ import annotations

from fastapi import APIRouter, Request

from ..config import settings
from ..signing import signer
from .proxy import gateway

router = APIRouter(tags=["gateway"])


@router.post("/v1/chat/completions")
async def chat_completions(request: Request):
    return await gateway.handle(request, "openai.chat")


@router.post("/v1/responses")
async def responses(request: Request):
    return await gateway.handle(request, "openai.responses")


@router.post("/v1/messages")
async def messages(request: Request):
    return await gateway.handle(request, "anthropic.messages")


@router.post("/v1/messages/count_tokens")
async def count_tokens(request: Request):
    return await gateway.passthrough(request, "anthropic.messages",
                                     f"{settings.anthropic_base_url}/v1/messages/count_tokens")


@router.get("/v1/models")
async def models(request: Request):
    if "anthropic-version" in request.headers:
        return await gateway.passthrough(request, "anthropic.messages", f"{settings.anthropic_base_url}/v1/models")
    return await gateway.passthrough(request, "openai.chat", f"{settings.openai_base_url}/models")


@router.get("/.well-known/jwks.json")
async def jwks():
    """Public key used to verify compliance tokens and ledger signatures."""
    return signer.jwks()
