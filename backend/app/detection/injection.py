"""Heuristic prompt injection and jailbreak detection.

Weighted signals are combined as independent evidence: score = 1 - prod(1 - w).
A single strong signal or two weaker ones cross the default threshold. This
layer is deliberately cheap. A model based classifier can be added through the
guard LLM detector for higher recall.
"""
from __future__ import annotations

import re

from .model import SEVERITY, Finding

THRESHOLD = 0.6

_SIGNALS: list[tuple[str, float, re.Pattern]] = [
    ("INJECTION_INSTRUCTION_OVERRIDE", 0.7, re.compile(
        r"(?i)\b(?:ignore|disregard|forget|override|bypass)\b[^.\n]{0,40}\b(?:all |any |the )?"
        r"(?:previous|prior|above|earlier|preceding|system|original)\b[^.\n]{0,30}"
        r"\b(?:instructions?|prompts?|rules?|polic(?:y|ies)|guidelines?|directions?|context)\b")),
    ("INJECTION_SYSTEM_PROMPT_EXTRACTION", 0.65, re.compile(
        r"(?i)\b(?:reveal|show|print|repeat|output|display|leak|tell me|what (?:is|are))\b[^.\n]{0,40}"
        r"\b(?:system prompt|hidden (?:prompt|instructions?|configuration)|initial instructions?|"
        r"developer (?:message|prompt)|your instructions)\b")),
    ("INJECTION_ROLE_HIJACK", 0.6, re.compile(
        r"(?i)\b(?:you are now|from now on you are|act as|pretend (?:to be|you are)|enter|enable|switch to)\b"
        r"[^.\n]{0,40}\b(?:DAN|developer mode|jailbreak|unrestricted|no restrictions|without (?:any )?"
        r"(?:restrictions|filters|rules)|god mode|evil)\b")),
    ("INJECTION_DELIMITER", 0.55, re.compile(
        r"(?i)(?:<\|im_start\|>|<\|im_end\|>|<\|system\|>|\[/?INST\]|<<SYS>>|^\s*#{2,}\s*(?:system|instruction)s?\b|"
        r"^\s*(?:system|assistant)\s*:\s)", re.MULTILINE)),
    ("INJECTION_CREDENTIAL_EXFILTRATION", 0.5, re.compile(
        r"(?i)\b(?:print|reveal|send|list|dump|exfiltrate|output)\b[^.\n]{0,40}"
        r"\b(?:api keys?|credentials?|secrets?|passwords?|access tokens?|environment variables)\b")),
    ("INJECTION_POLICY_EVASION", 0.45, re.compile(
        r"(?i)\b(?:do not|don't|never)\b[^.\n]{0,20}\b(?:refuse|mention|apply|follow)\b[^.\n]{0,30}"
        r"\b(?:polic(?:y|ies)|guidelines|safety|restrictions|filters?)\b")),
    ("INJECTION_ENCODED_PAYLOAD", 0.4, re.compile(
        r"(?i)\b(?:decode|base64|rot13)\b[^.\n]{0,40}\b(?:and (?:then )?(?:execute|follow|run|obey))\b")),
]


def scan_injection(text: str, threshold: float = THRESHOLD) -> list[Finding]:
    hits: list[tuple[str, float, re.Match]] = []
    for label, weight, regex in _SIGNALS:
        match = regex.search(text)
        if match:
            hits.append((label, weight, match))
    if not hits:
        return []
    remaining = 1.0
    for _, weight, _ in hits:
        remaining *= 1.0 - weight
    score = 1.0 - remaining
    if score < threshold:
        return []
    label, _, match = max(hits, key=lambda h: h[1])
    severity = SEVERITY["high"] if score >= 0.85 else SEVERITY["medium"]
    return [Finding("injection", "injection", label, match.start(), match.end(), round(score, 2), severity,
                    text=match.group(0))]
