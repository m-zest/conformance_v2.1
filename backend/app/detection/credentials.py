"""Credential and secret detection: provider token formats plus an entropy check for generic secrets."""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from .model import SEVERITY, Finding


@dataclass(frozen=True)
class SecretSpec:
    entity_type: str
    severity: str
    confidence: float
    regex: re.Pattern
    group: int = 0


SECRET_PATTERNS: list[SecretSpec] = [
    SecretSpec("PRIVATE_KEY", "critical", 0.99,
               re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----[\s\S]{20,}?(?:-----END (?:[A-Z]+ )?PRIVATE KEY-----|\Z)")),
    SecretSpec("AWS_ACCESS_KEY_ID", "critical", 0.97, re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    SecretSpec("AWS_SECRET_ACCESS_KEY", "critical", 0.95,
               re.compile(r"(?i)aws_?secret_?(?:access_?)?key[\"'\s]*[:=][\"'\s]*([A-Za-z0-9/+=]{40})\b"), group=1),
    SecretSpec("GITHUB_TOKEN", "critical", 0.98,
               re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,255}|github_pat_[A-Za-z0-9_]{60,255})\b")),
    SecretSpec("SLACK_TOKEN", "high", 0.97, re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{20,}\b")),
    SecretSpec("ANTHROPIC_API_KEY", "critical", 0.98, re.compile(r"\bsk-ant-[A-Za-z0-9_-]{24,}\b")),
    SecretSpec("OPENAI_API_KEY", "critical", 0.95, re.compile(r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,}\b")),
    SecretSpec("GOOGLE_API_KEY", "high", 0.95, re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    SecretSpec("STRIPE_SECRET_KEY", "critical", 0.97, re.compile(r"\b[sr]k_live_[0-9a-zA-Z]{24,}\b")),
    SecretSpec("AZURE_STORAGE_KEY", "critical", 0.95,
               re.compile(r"(?i)AccountKey=([A-Za-z0-9+/]{60,}={0,2})"), group=1),
    SecretSpec("DATABASE_URL", "high", 0.95,
               re.compile(r"\b(?:postgres(?:ql)?|mysql|mariadb|mongodb(?:\+srv)?|redis|amqps?|mssql)://"
                          r"[^\s:@/]+:([^\s@/]{4,})@[^\s/\"']+")),
    SecretSpec("JWT", "high", 0.9,
               re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{16,}\b")),
]

_ASSIGNMENT = re.compile(
    r"(?i)\b(?:[a-z0-9_]*(?:password|passwd|pwd|secret|api[_-]?key|access[_-]?key|auth[_-]?token|token|"
    r"client[_-]?secret|private[_-]?key))\b[\"']?\s*(?::|=|=>)\s*[\"']?([^\s\"',;]{8,120})")
_PLACEHOLDER = re.compile(
    r"(?i)^(?:x{4,}|\*{4,}|<.*>|\$\{.*\}|\{\{.*\}\}|%.*%|your[_-].*|changeme.*|example.*|placeholder.*|"
    r"redacted.*|none|null|true|false|undefined|\[.*\]|os\.environ.*|process\.env.*|getenv.*|secrets?\..*)$")


def shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = Counter(value)
    n = len(value)
    return -sum(c / n * math.log2(c / n) for c in counts.values())


def scan_secrets(text: str) -> list[Finding]:
    findings: list[Finding] = []
    covered: list[tuple[int, int]] = []
    for spec in SECRET_PATTERNS:
        for match in spec.regex.finditer(text):
            start, end = match.span(spec.group)
            findings.append(Finding("secret", "secret.credential", spec.entity_type, start, end, spec.confidence,
                                    SEVERITY[spec.severity], text=match.group(spec.group)))
            covered.append((start, end))
    for match in _ASSIGNMENT.finditer(text):
        value = match.group(1)
        start, end = match.span(1)
        if any(s <= start < e for s, e in covered):
            continue
        if _PLACEHOLDER.match(value) or value.isalpha() or shannon_entropy(value) < 3.0:
            continue
        if not (any(c.isdigit() for c in value) and any(c.isalpha() for c in value)):
            continue
        findings.append(Finding("secret", "secret.credential", "GENERIC_SECRET", start, end, 0.75,
                                SEVERITY["high"], text=value))
    return findings
