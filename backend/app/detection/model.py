"""Shared detection types."""
from __future__ import annotations

from dataclasses import dataclass

SEVERITY = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
SEVERITY_NAMES = {v: k for k, v in SEVERITY.items()}

CATEGORIES = {
    "secret.credential": "Credentials and secrets",
    "pii.financial": "Financial identifiers",
    "pii.identity": "Government and national IDs",
    "pii.health": "Health information",
    "pii.contact": "Contact details",
    "pii.person": "Names and locations",
    "confidential": "Confidential business data",
    "injection": "Prompt injection",
    "content_safety": "Unsafe content",
}

# Categories whose matched text is a sensitive value and can be replaced by a placeholder.
MASKABLE = {"secret.credential", "pii.financial", "pii.identity", "pii.health", "pii.contact", "pii.person",
            "confidential"}

ENTITY_LABELS = {
    "CREDIT_CARD": "payment card number", "IBAN": "IBAN", "IT_FISCAL_CODE": "Italian fiscal code",
    "US_SSN": "US social security number", "ES_DNI": "Spanish DNI or NIE", "UK_NINO": "UK national insurance number",
    "FR_NIR": "French social security number", "DE_TAX_ID": "German tax ID", "PASSPORT_NUMBER": "passport number",
    "MEDICAL_RECORD_NUMBER": "medical record number", "DATE_OF_BIRTH": "date of birth",
    "EMAIL_ADDRESS": "email address", "PHONE_NUMBER": "phone number", "IP_ADDRESS": "IP address",
    "CONFIDENTIAL_MARKER": "confidentiality marking", "PERSON": "person name", "LOCATION": "location",
    "PRIVATE_KEY": "private key", "AWS_ACCESS_KEY_ID": "AWS access key", "AWS_SECRET_ACCESS_KEY": "AWS secret key",
    "GITHUB_TOKEN": "GitHub token", "SLACK_TOKEN": "Slack token", "ANTHROPIC_API_KEY": "Anthropic API key",
    "OPENAI_API_KEY": "OpenAI API key", "GOOGLE_API_KEY": "Google API key", "STRIPE_SECRET_KEY": "Stripe secret key",
    "AZURE_STORAGE_KEY": "Azure storage key", "DATABASE_URL": "database connection string",
    "JWT": "JSON web token", "GENERIC_SECRET": "password or secret",
    "INJECTION_INSTRUCTION_OVERRIDE": "instruction override", "INJECTION_SYSTEM_PROMPT_EXTRACTION":
    "system prompt extraction", "INJECTION_ROLE_HIJACK": "role hijack", "INJECTION_DELIMITER": "delimiter injection",
    "INJECTION_CREDENTIAL_EXFILTRATION": "credential exfiltration request",
    "INJECTION_POLICY_EVASION": "policy evasion request", "INJECTION_ENCODED_PAYLOAD": "encoded payload",
}


def entity_label(entity_type: str) -> str:
    if entity_type in ENTITY_LABELS:
        return ENTITY_LABELS[entity_type]
    return entity_type.replace("UNSAFE_", "unsafe content: ").replace("_", " ").lower()


ACTIONS = ("allow", "log", "mask", "block")
ACTION_RANK = {"allow": 0, "log": 1, "mask": 2, "block": 3}


@dataclass(slots=True)
class Finding:
    detector: str
    category: str
    entity_type: str
    start: int
    end: int
    confidence: float
    severity: int
    text: str = ""          # matched value, kept in memory only for the lifetime of the request
    segment: int = 0
    direction: str = "prompt"
    action: str = "log"
    fingerprint: str = ""
    is_new: bool = True
    preview: str = ""

    def clone(self, **changes) -> "Finding":
        data = {name: getattr(self, name) for name in self.__slots__}
        data.update(changes)
        return Finding(**data)


def safe_preview(entity_type: str, value: str) -> str:
    """A short description that helps an analyst recognise the item without storing the value."""
    v = value.strip()
    if not v:
        return ""
    if entity_type == "EMAIL_ADDRESS" and "@" in v:
        local, _, domain = v.partition("@")
        return f"{local[:1]}***@{domain}"
    if entity_type in {"CREDIT_CARD", "IBAN", "PHONE_NUMBER"}:
        digits = "".join(ch for ch in v if ch.isalnum())
        return f"{'*' * 4} {digits[-4:]} ({len(digits)} chars)"
    if entity_type in {"PERSON", "LOCATION"}:
        return " ".join(part[:1] + "." for part in v.split()[:3])
    if entity_type.startswith(("AWS", "GITHUB", "SLACK", "OPENAI", "ANTHROPIC", "GOOGLE", "STRIPE")):
        return f"{v[:4]}*** ({len(v)} chars)"
    if entity_type in {"PRIVATE_KEY", "DATABASE_URL", "GENERIC_SECRET", "JWT", "AZURE_STORAGE_KEY"}:
        return f"({len(v)} chars)"
    if entity_type.startswith(("INJECTION", "UNSAFE")) or entity_type in {"CONFIDENTIAL_MARKER"}:
        return v[:60]
    return f"{'*' * 4}{v[-2:]} ({len(v)} chars)"
