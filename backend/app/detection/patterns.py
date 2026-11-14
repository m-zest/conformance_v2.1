"""Deterministic PII detection: regular expressions with checksum and context validation.

Each pattern is cheap to evaluate and is paired with a validator wherever the
format has a checksum, so that a random digit string is not reported as a card
number or an IBAN. Patterns that are ambiguous on their own require a context
word near the match.
"""
from __future__ import annotations

import re
import string
from dataclasses import dataclass
from typing import Callable

from .model import SEVERITY, Finding

_ODD = {
    **{str(i): v for i, v in enumerate([1, 0, 5, 7, 9, 13, 15, 17, 19, 21])},
    **dict(zip(string.ascii_uppercase,
               [1, 0, 5, 7, 9, 13, 15, 17, 19, 21, 2, 4, 18, 20, 11, 3, 6, 8, 12, 14, 16, 10, 22, 25, 24, 23])),
}
_EVEN = {**{str(i): i for i in range(10)}, **{c: i for i, c in enumerate(string.ascii_uppercase)}}
_IBAN_LENGTHS = {
    "AT": 20, "BE": 16, "BG": 22, "CH": 21, "CY": 28, "CZ": 24, "DE": 22, "DK": 18, "EE": 20, "ES": 24,
    "FI": 18, "FR": 27, "GB": 22, "GR": 27, "HR": 21, "HU": 28, "IE": 22, "IS": 26, "IT": 27, "LI": 21,
    "LT": 20, "LU": 20, "LV": 21, "MC": 27, "MT": 31, "NL": 18, "NO": 15, "PL": 28, "PT": 25, "RO": 24,
    "SE": 24, "SI": 19, "SK": 24, "SM": 27,
}


def luhn_valid(value: str) -> bool:
    digits = [int(c) for c in value if c.isdigit()]
    if not 13 <= len(digits) <= 19 or len(set(digits)) == 1:
        return False
    if digits[0] not in (2, 3, 4, 5, 6):
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def iban_valid(value: str) -> bool:
    raw = re.sub(r"\s", "", value).upper()
    expected = _IBAN_LENGTHS.get(raw[:2])
    if expected is None or len(raw) != expected:
        return False
    rearranged = raw[4:] + raw[:4]
    try:
        return int("".join(str(int(c, 36)) for c in rearranged)) % 97 == 1
    except ValueError:
        return False


def codice_fiscale_valid(value: str) -> bool:
    v = value.upper()
    if len(v) != 16:
        return False
    total = sum(_ODD[c] if i % 2 == 0 else _EVEN[c] for i, c in enumerate(v[:15]))
    return string.ascii_uppercase[total % 26] == v[15]


def es_dni_valid(value: str) -> bool:
    v = value.upper()
    number = v[:-1].replace("X", "0").replace("Y", "1").replace("Z", "2")
    return number.isdigit() and "TRWAGMYFPDXBNJZSQVHLCKE"[int(number) % 23] == v[-1]


def fr_nir_valid(value: str) -> bool:
    digits = re.sub(r"\s", "", value)
    if len(digits) != 15 or not digits.isdigit():
        return False
    return 97 - int(digits[:13]) % 97 == int(digits[13:])


def phone_valid(value: str) -> bool:
    digits = sum(c.isdigit() for c in value)
    return 8 <= digits <= 15


def ipv4_public(value: str) -> bool:
    parts = [int(p) for p in value.split(".")]
    if any(p > 255 for p in parts):
        return False
    a, b = parts[0], parts[1]
    if a in (0, 10, 127) or a >= 224 or (a == 192 and b == 168) or (a == 172 and 16 <= b <= 31) or (
            a == 169 and b == 254):
        return False
    return True


@dataclass(frozen=True)
class PatternSpec:
    entity_type: str
    category: str
    severity: str
    confidence: float
    regex: re.Pattern
    validator: Callable[[str], bool] | None = None
    context: re.Pattern | None = None   # must appear within the window before the match
    group: int = 0


def _ctx(words: str) -> re.Pattern:
    return re.compile(words, re.IGNORECASE)


PATTERNS: list[PatternSpec] = [
    PatternSpec("CREDIT_CARD", "pii.financial", "high", 0.95,
                re.compile(r"(?<![\w.-])\d(?:[ -]?\d){12,18}(?![\w-])"), luhn_valid),
    PatternSpec("IBAN", "pii.financial", "high", 0.97,
                re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,4})?\b"), iban_valid),
    PatternSpec("IT_FISCAL_CODE", "pii.identity", "high", 0.97,
                re.compile(r"\b[A-Za-z]{6}\d{2}[A-EHLMPR-Ta-ehlmpr-t]\d{2}[A-Za-z]\d{3}[A-Za-z]\b"),
                codice_fiscale_valid),
    PatternSpec("US_SSN", "pii.identity", "high", 0.85,
                re.compile(r"\b(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b")),
    PatternSpec("US_SSN", "pii.identity", "high", 0.8,
                re.compile(r"\b(?!000|666|9\d\d)\d{3}(?!00)\d{2}(?!0000)\d{4}\b"),
                context=_ctx(r"\b(?:ssn|social security)\b")),
    PatternSpec("ES_DNI", "pii.identity", "high", 0.85,
                re.compile(r"\b(?:\d{8}|[XYZxyz]\d{7})[A-Za-z]\b"), es_dni_valid,
                context=_ctx(r"\b(?:dni|nie|nif|documento|identidad)\b")),
    PatternSpec("UK_NINO", "pii.identity", "high", 0.85,
                re.compile(r"\b(?!BG|GB|NK|KN|TN|NT|ZZ)[A-CEGHJ-PR-TW-Z][A-CEGHJ-NPR-TW-Z] ?\d{2} ?\d{2} ?\d{2} ?[A-D]\b")),
    PatternSpec("FR_NIR", "pii.identity", "high", 0.9,
                re.compile(r"\b[12] ?\d{2} ?(?:0[1-9]|1[0-2]) ?\d{2} ?\d{3} ?\d{3} ?\d{2}\b"), fr_nir_valid),
    PatternSpec("DE_TAX_ID", "pii.identity", "high", 0.8,
                re.compile(r"\b[1-9]\d{10}\b"),
                context=_ctx(r"(?:steuer-?id|steueridentifikationsnummer|idnr|tax id)")),
    PatternSpec("PASSPORT_NUMBER", "pii.identity", "high", 0.75,
                re.compile(r"\b[A-Z]{1,2}\d{6,8}\b"),
                context=_ctx(r"\b(?:passport|passaporto|reisepass|passeport)\b")),
    PatternSpec("MEDICAL_RECORD_NUMBER", "pii.health", "high", 0.9,
                re.compile(r"\b(?:MRN|medical record(?: number| no\.?)?|patient id)[\s:#]*([A-Z0-9][A-Z0-9-]{5,11})\b",
                           re.IGNORECASE), group=1),
    PatternSpec("DATE_OF_BIRTH", "pii.identity", "medium", 0.8,
                re.compile(r"\b(?:born(?: on)?|dob|date of birth|nato il|nata il|geboren(?: am)?|n[ée]e? le)"
                           r"[\s:]*(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|\d{4}-\d{2}-\d{2})", re.IGNORECASE), group=1),
    PatternSpec("EMAIL_ADDRESS", "pii.contact", "low", 0.98,
                re.compile(r"(?<![\w.+-])[A-Za-z0-9][A-Za-z0-9._%+-]{0,63}@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
                           r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)*\.[A-Za-z]{2,}\b")),
    PatternSpec("PHONE_NUMBER", "pii.contact", "low", 0.85,
                re.compile(r"(?<![\w+])\+\d{1,3}[ .-]?(?:\(?\d{1,4}\)?[ .-]?){1,4}\d{2,4}(?!\w)"), phone_valid),
    PatternSpec("PHONE_NUMBER", "pii.contact", "low", 0.7,
                re.compile(r"(?<![\w+.-])\(?0?\d{2,4}\)?[ .-]\d{3,4}[ .-]?\d{3,4}(?![\w-])"), phone_valid,
                context=_ctx(r"\b(?:phone|tel|telephone|mobile|cell|call|fax|whatsapp|telefono|cellulare)\b")),
    PatternSpec("IP_ADDRESS", "pii.contact", "info", 0.6,
                re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])"), ipv4_public,
                context=_ctx(r"\b(?:ip|address|client|user|customer|login|from)\b")),
    PatternSpec("CONFIDENTIAL_MARKER", "confidential", "medium", 0.9,
                re.compile(r"\b(?:strictly confidential|company confidential|highly confidential|"
                           r"confidential[ ,:-]+(?:do not|not for) (?:share|distribut\w+|forward\w*)|"
                           r"internal use only|for internal use|not for (?:external )?distribution|"
                           r"attorney[- ]client privileged|privileged (?:and|&) confidential|trade secret|"
                           r"riservato e confidenziale|streng vertraulich)\b", re.IGNORECASE)),
]

CONTEXT_WINDOW = 60


def scan_patterns(text: str) -> list[Finding]:
    findings: list[Finding] = []
    for spec in PATTERNS:
        for match in spec.regex.finditer(text):
            value = match.group(spec.group)
            start, end = match.span(spec.group)
            if spec.validator and not spec.validator(value):
                continue
            if spec.context and not spec.context.search(text, max(0, start - CONTEXT_WINDOW), start):
                continue
            findings.append(Finding("pattern", spec.category, spec.entity_type, start, end, spec.confidence,
                                    SEVERITY[spec.severity], text=value))
    return findings
