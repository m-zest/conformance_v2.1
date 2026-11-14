"""Content safety classification with a guard model (Llama Guard).

The guard model runs on infrastructure you control, either through Ollama or
any OpenAI-compatible server such as vLLM. It answers "safe" or "unsafe" plus
hazard category codes. It complements the deterministic detectors: it does not
find card numbers or keys, it judges what the request is asking for.
"""
from __future__ import annotations

import logging
import time

import httpx

from ..config import settings
from .model import SEVERITY, Finding

log = logging.getLogger("conformance.detection.guard")

HAZARDS = {
    "S1": ("VIOLENT_CRIMES", "high"), "S2": ("NON_VIOLENT_CRIMES", "medium"), "S3": ("SEX_RELATED_CRIMES", "high"),
    "S4": ("CHILD_SEXUAL_EXPLOITATION", "critical"), "S5": ("DEFAMATION", "medium"),
    "S6": ("SPECIALIZED_ADVICE", "low"), "S7": ("PRIVACY", "medium"), "S8": ("INTELLECTUAL_PROPERTY", "medium"),
    "S9": ("INDISCRIMINATE_WEAPONS", "critical"), "S10": ("HATE", "high"), "S11": ("SUICIDE_SELF_HARM", "high"),
    "S12": ("SEXUAL_CONTENT", "medium"), "S13": ("ELECTIONS", "low"), "S14": ("CODE_INTERPRETER_ABUSE", "high"),
}


def parse_guard_output(output: str) -> list[str]:
    """Return hazard codes from a Llama Guard reply. An empty list means safe."""
    lines = [line.strip() for line in output.strip().splitlines() if line.strip()]
    if not lines or lines[0].lower() != "unsafe":
        return []
    codes = [c.strip().upper() for c in ",".join(lines[1:]).split(",") if c.strip()]
    return codes or ["S0"]


class GuardLLM:
    name = "guard_llm"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.enabled = settings.guard_enabled
        self.inline = settings.guard_mode == "inline"
        self._client = client
        self.last_error = ""
        self.last_latency_ms: float | None = None
        self.calls = 0
        self.failures = 0

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=settings.guard_timeout)
        return self._client

    async def _complete(self, text: str) -> str:
        messages = [{"role": "user", "content": text}]
        if settings.guard_backend == "openai":
            resp = await self._http().post(f"{settings.guard_url}/v1/chat/completions", json={
                "model": settings.guard_model, "messages": messages, "temperature": 0, "max_tokens": 32})
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        resp = await self._http().post(f"{settings.guard_url}/api/chat", json={
            "model": settings.guard_model, "messages": messages, "stream": False, "options": {"temperature": 0}})
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    async def classify(self, text: str) -> list[Finding]:
        """Classify one piece of text. Fails open: an unreachable guard never blocks traffic."""
        if not self.enabled or not text.strip():
            return []
        text = text[: settings.guard_max_chars]
        started = time.perf_counter()
        self.calls += 1
        try:
            output = await self._complete(text)
            self.last_error = ""
        except Exception as exc:
            self.failures += 1
            self.last_error = f"{type(exc).__name__}: {exc}"[:300]
            log.warning("guard model call failed: %s", self.last_error)
            return []
        finally:
            self.last_latency_ms = round((time.perf_counter() - started) * 1000, 1)
        findings = []
        for code in parse_guard_output(output):
            label, severity = HAZARDS.get(code, ("POLICY_VIOLATION", "medium"))
            findings.append(Finding("guard_llm", "content_safety", f"UNSAFE_{label}", 0, min(len(text), 120), 0.9,
                                    SEVERITY[severity], text=text[:120]))
        return findings

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()

    def status(self) -> dict:
        if not self.enabled:
            state, detail = "disabled", "Set GUARD_LLM_ENABLED=true and start the guard profile to enable."
        elif self.last_error:
            state, detail = "unavailable", self.last_error
        else:
            state = "ready"
            detail = f"{settings.guard_model} via {settings.guard_backend}, {settings.guard_mode} mode"
            if self.last_latency_ms is not None:
                detail += f", last call {self.last_latency_ms} ms"
        return {"id": "guard_llm", "name": "Guard model (Llama Guard)", "state": state, "detail": detail}
