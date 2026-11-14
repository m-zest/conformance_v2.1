"""Detection orchestrator: runs the detectors, resolves overlaps, caches results and redacts text."""
from __future__ import annotations

import hashlib
import hmac
import re
import threading
from collections import Counter, OrderedDict
from dataclasses import dataclass
from typing import Callable

import anyio

from ..config import settings
from .guard_llm import GuardLLM
from .injection import scan_injection
from .ner import NerDetector
from .patterns import scan_patterns
from .credentials import scan_secrets
from .model import MASKABLE, SEVERITY, Finding, safe_preview

DETECTOR_SET_VERSION = "2026.11"
_CACHE_MAX = 4000
_CACHE_MIN_CHARS = 200
_THREAD_THRESHOLD = 30_000


@dataclass
class Segment:
    """One piece of text inside a request, with a setter to write a redacted version back."""

    text: str
    role: str
    setter: Callable[[str], None] | None = None


def compile_custom_terms(terms: list[dict]) -> list[tuple[str, int, re.Pattern]]:
    compiled = []
    for term in terms or []:
        pattern = (term.get("pattern") or "").strip()
        if not pattern:
            continue
        label = re.sub(r"[^A-Z0-9_]", "_", (term.get("label") or "CUSTOM_TERM").upper())[:40] or "CUSTOM_TERM"
        severity = SEVERITY.get(term.get("severity", "medium"), 2)
        try:
            regex = re.compile(pattern if term.get("type") == "regex" else r"(?<!\w)" + re.escape(pattern) + r"(?!\w)",
                               re.IGNORECASE)
        except re.error:
            continue
        compiled.append((label, severity, regex))
    return compiled


def resolve_overlaps(findings: list[Finding]) -> list[Finding]:
    """Keep the strongest finding where spans overlap (severity, then confidence, then length)."""
    ranked = sorted(findings, key=lambda f: (-f.severity, -f.confidence, -(f.end - f.start), f.start))
    kept: list[Finding] = []
    for f in ranked:
        if f.category in ("injection", "content_safety") or not any(
                f.start < k.end and k.start < f.end for k in kept if k.category not in ("injection", "content_safety")):
            kept.append(f)
    return sorted(kept, key=lambda f: f.start)


class Redactor:
    """Replaces sensitive values with placeholders that stay consistent within one request."""

    def __init__(self) -> None:
        self._map: dict[tuple[str, str], str] = {}
        self._counters: Counter = Counter()

    def placeholder(self, finding: Finding) -> str:
        key = (finding.entity_type, finding.text.strip().lower())
        if key not in self._map:
            self._counters[finding.entity_type] += 1
            self._map[key] = f"[{finding.entity_type}_{self._counters[finding.entity_type]}]"
        return self._map[key]

    def apply(self, text: str, findings: list[Finding]) -> str:
        out, pos = [], 0
        for f in sorted(findings, key=lambda x: x.start):
            if f.start < pos or f.category not in MASKABLE:
                continue
            out.append(text[pos:f.start])
            out.append(self.placeholder(f))
            pos = f.end
        out.append(text[pos:])
        return "".join(out)


def fingerprint(entity_type: str, value: str) -> str:
    normalized = re.sub(r"[\s-]", "", value).lower()
    digest = hmac.new(settings.secret_key.encode(), f"{entity_type}:{normalized}".encode(), hashlib.sha256)
    return digest.hexdigest()[:24]


def finalize_findings(findings: list[Finding]) -> None:
    for f in findings:
        f.fingerprint = fingerprint(f.entity_type, f.text)
        f.preview = safe_preview(f.entity_type, f.text) if settings.store_previews else ""


class DetectionEngine:
    def __init__(self) -> None:
        self.ner = NerDetector()
        self.guard = GuardLLM()
        self._cache: OrderedDict[tuple, list[tuple]] = OrderedDict()
        self._lock = threading.Lock()
        self._terms_cache: dict[str, list] = {}
        self.cache_hits = 0
        self.cache_misses = 0

    def _terms(self, custom_terms: list[dict]) -> tuple[str, list]:
        sig = hashlib.sha1(repr(custom_terms).encode()).hexdigest()[:12] if custom_terms else ""
        if sig and sig not in self._terms_cache:
            if len(self._terms_cache) > 64:
                self._terms_cache.clear()
            self._terms_cache[sig] = compile_custom_terms(custom_terms)
        return sig, self._terms_cache.get(sig, [])

    def scan_text(self, text: str, custom_terms: list[dict] | None = None, *, use_ner: bool = True) -> list[Finding]:
        """Run every synchronous detector over one text and return non-overlapping findings."""
        if not text or not text.strip():
            return []
        sig, terms = self._terms(custom_terms or [])
        use_ner = use_ner and self.ner.available
        key = None
        if len(text) >= _CACHE_MIN_CHARS:
            key = (hashlib.sha1(text.encode("utf-8", "ignore")).digest(), sig, use_ner)
            with self._lock:
                cached = self._cache.get(key)
                if cached is not None:
                    self._cache.move_to_end(key)
                    self.cache_hits += 1
                    return [Finding(d, c, e, s, en, conf, sev, text=text[s:en]) for d, c, e, s, en, conf, sev in cached]
            self.cache_misses += 1
        findings = scan_secrets(text) + scan_patterns(text) + scan_injection(text)
        for label, severity, regex in terms:
            for m in regex.finditer(text):
                findings.append(Finding("custom", "confidential", label, m.start(), m.end(), 1.0, severity,
                                        text=m.group(0)))
        if use_ner:
            findings += self.ner.scan(text)
        findings = resolve_overlaps(findings)
        if key is not None:
            with self._lock:
                self._cache[key] = [(f.detector, f.category, f.entity_type, f.start, f.end, f.confidence, f.severity)
                                    for f in findings]
                if len(self._cache) > _CACHE_MAX:
                    self._cache.popitem(last=False)
        return findings

    def _scan_segments_sync(self, segments: list[Segment], custom_terms: list[dict]) -> tuple[list[Finding], bool]:
        findings: list[Finding] = []
        budget = settings.max_scan_chars
        ner_budget = settings.ner_max_chars
        truncated = False
        # Newest content first so that budgets are spent on what the user just sent.
        for index in range(len(segments) - 1, -1, -1):
            seg = segments[index]
            if seg.role == "assistant" or not seg.text:
                continue
            if budget <= 0:
                truncated = True
                break
            text = seg.text
            if len(text) > budget:
                truncated = True
                continue
            budget -= len(text)
            use_ner = seg.role in ("user", "tool") and len(text) <= ner_budget
            if use_ner:
                ner_budget -= len(text)
            for f in self.scan_text(text, custom_terms, use_ner=use_ner):
                f.segment = index
                findings.append(f)
        return findings, truncated

    async def scan_segments(self, segments: list[Segment], custom_terms: list[dict]) -> tuple[list[Finding], bool]:
        total = sum(len(s.text) for s in segments)
        if total > _THREAD_THRESHOLD:
            return await anyio.to_thread.run_sync(self._scan_segments_sync, segments, custom_terms)
        return self._scan_segments_sync(segments, custom_terms)

    def status(self) -> list[dict]:
        base = [
            {"id": "pattern", "name": "PII patterns with checksum validation", "state": "ready",
             "detail": "Cards, IBAN, national IDs, contact details, confidentiality markers"},
            {"id": "secret", "name": "Credential and secret formats", "state": "ready",
             "detail": "Cloud keys, tokens, private keys, connection strings, entropy check"},
            {"id": "injection", "name": "Prompt injection heuristics", "state": "ready",
             "detail": "Weighted signals for instruction override, extraction and role hijack"},
            {"id": "custom", "name": "Custom terms", "state": "ready",
             "detail": "Keywords and regular expressions defined per policy"},
        ]
        return base + [self.ner.status(), self.guard.status()]


engine = DetectionEngine()
