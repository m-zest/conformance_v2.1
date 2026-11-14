"""Runtime configuration. All settings come from environment variables."""
from __future__ import annotations

import os
import secrets
from pathlib import Path

VERSION = "3.0.0"
DEFAULT_ADMIN_PASSWORD = "ChangeMe-Pilot-2026"


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw not in (None, "") else default


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw not in (None, "") else default


def _str(name: str, default: str = "") -> str:
    raw = os.getenv(name)
    return raw if raw not in (None, "") else default


class Settings:
    def __init__(self) -> None:
        self.data_dir = Path(_str("DATA_DIR", "./data")).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.database_url = _str("DATABASE_URL", f"sqlite+aiosqlite:///{self.data_dir / 'conformance.db'}")
        self.secret_key = self._load_secret()

        # Dashboard access
        self.admin_email = _str("ADMIN_EMAIL", "admin@meridian.example").lower()
        self.admin_password = _str("ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)
        self.session_hours = _int("SESSION_HOURS", 8)
        self.cookie_secure = _bool("COOKIE_SECURE", False)
        self.dashboard_url = _str("DASHBOARD_URL", "http://localhost:8080").rstrip("/")

        # Upstream model providers
        self.openai_base_url = _str("OPENAI_BASE_URL", "http://localhost:9000/v1").rstrip("/")
        self.openai_api_key = _str("OPENAI_API_KEY", "simulator")
        self.openai_auth_style = _str("OPENAI_AUTH_STYLE", "bearer")  # bearer | api-key (Azure OpenAI)
        self.anthropic_base_url = _str("ANTHROPIC_BASE_URL", "http://localhost:9000").rstrip("/")
        self.anthropic_api_key = _str("ANTHROPIC_API_KEY", "simulator")
        self.upstream_timeout = _float("UPSTREAM_TIMEOUT_SECONDS", 600.0)
        self.max_body_bytes = _int("MAX_BODY_BYTES", 20 * 1024 * 1024)

        # Identity
        self.oidc_issuer = _str("OIDC_ISSUER")
        self.oidc_audience = _str("OIDC_AUDIENCE")
        self.oidc_jwks_url = _str("OIDC_JWKS_URL")
        self.oidc_email_claim = _str("OIDC_EMAIL_CLAIM", "email")
        self.oidc_name_claim = _str("OIDC_NAME_CLAIM", "name")
        self.oidc_team_claim = _str("OIDC_TEAM_CLAIM", "department")
        self.oidc_default_app = _str("OIDC_DEFAULT_APP", "developer-tools")

        # Detection
        self.max_scan_chars = _int("MAX_SCAN_CHARS", 400_000)
        self.ner_enabled = _bool("NER_ENABLED", True)
        self.ner_model = _str("NER_MODEL", "en_core_web_sm")
        self.ner_language = _str("NER_LANGUAGE", "en")
        self.ner_entities = [e.strip() for e in _str("NER_ENTITIES", "PERSON,LOCATION").split(",") if e.strip()]
        self.ner_max_chars = _int("NER_MAX_CHARS", 20_000)
        self.guard_enabled = _bool("GUARD_LLM_ENABLED", False)
        self.guard_backend = _str("GUARD_LLM_BACKEND", "ollama")  # ollama | openai
        self.guard_url = _str("GUARD_LLM_URL", "http://ollama:11434").rstrip("/")
        self.guard_model = _str("GUARD_LLM_MODEL", "llama-guard3:1b")
        self.guard_mode = _str("GUARD_LLM_MODE", "async")  # async | inline
        self.guard_timeout = _float("GUARD_LLM_TIMEOUT_SECONDS", 8.0)
        self.guard_max_chars = _int("GUARD_LLM_MAX_CHARS", 6000)

        # Storage and privacy
        self.store_prompts = _str("STORE_PROMPTS", "redacted")  # redacted | none | full
        self.store_responses = _bool("STORE_RESPONSES", True)
        self.store_previews = _bool("STORE_FINDING_PREVIEWS", True)
        self.max_stored_chars = _int("MAX_STORED_CHARS", 8000)
        self.retention_days = _int("RETENTION_DAYS", 180)

        # Compliance signing
        self.signing_enabled = _bool("SIGNING_ENABLED", True)
        self.signing_key_path = Path(_str("SIGNING_KEY_PATH", str(self.data_dir / "keys" / "signing_es256.pem")))
        self.signing_issuer = _str("SIGNING_ISSUER", "conformance-gateway")
        self.signing_audience = _str("SIGNING_AUDIENCE", "llm-upstream")
        self.signing_ttl = _int("SIGNING_TTL_SECONDS", 120)

        # Alert notifications
        self.notify_min_severity = _str("NOTIFY_MIN_SEVERITY", "high")
        self.slack_webhook_url = _str("SLACK_WEBHOOK_URL")
        self.teams_webhook_url = _str("TEAMS_WEBHOOK_URL")
        self.alert_webhook_url = _str("ALERT_WEBHOOK_URL")
        self.smtp_host = _str("SMTP_HOST")
        self.smtp_port = _int("SMTP_PORT", 587)
        self.smtp_user = _str("SMTP_USER")
        self.smtp_password = _str("SMTP_PASSWORD")
        self.smtp_from = _str("SMTP_FROM")
        self.smtp_to = [a.strip() for a in _str("SMTP_TO").split(",") if a.strip()]
        self.smtp_starttls = _bool("SMTP_STARTTLS", True)

        # Connectors (observed tools)
        self.connector_poll_seconds = _int("CONNECTOR_POLL_SECONDS", 300)
        self.m365_mode = _str("M365_COPILOT_MODE", "disabled")  # disabled | demo | live
        self.m365_tenant_id = _str("M365_TENANT_ID", "demo-tenant")
        self.m365_client_id = _str("M365_CLIENT_ID", "demo-client")
        self.m365_client_secret = _str("M365_CLIENT_SECRET", "demo-secret")
        self.m365_login_url = _str("M365_LOGIN_URL", "https://login.microsoftonline.com").rstrip("/")
        self.m365_graph_url = _str("M365_GRAPH_URL", "https://graph.microsoft.com").rstrip("/")
        self.m365_lookback_days = _int("M365_LOOKBACK_DAYS", 14)
        self.github_mode = _str("GITHUB_COPILOT_MODE", "disabled")  # disabled | demo | live
        self.github_api_url = _str("GITHUB_API_URL", "https://api.github.com").rstrip("/")
        self.github_org = _str("GITHUB_ORG", "meridian-group")
        self.github_token = _str("GITHUB_TOKEN", "demo-token")
        self.github_usage_report_path = _str(
            "GITHUB_USAGE_REPORT_PATH", "/orgs/{org}/copilot/metrics/reports/users-1-day")
        self.github_lookback_days = _int("GITHUB_LOOKBACK_DAYS", 14)
        self.simulator_url = _str("SIMULATOR_URL", "http://localhost:9000").rstrip("/")

        # Demo
        self.demo_mode = _bool("DEMO_MODE", False)
        self.demo_seed = _bool("DEMO_SEED", False)
        self.demo_seed_days = _int("DEMO_SEED_DAYS", 14)
        self.demo_app_key = _str("DEMO_APP_KEY")
        self.pricing_path = _str("PRICING_PATH")

    def _load_secret(self) -> str:
        value = _str("SECRET_KEY")
        if value:
            return value
        path = self.data_dir / "secret.key"
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
        value = secrets.token_urlsafe(48)
        path.write_text(value, encoding="utf-8")
        path.chmod(0o600)
        return value

    @property
    def using_default_admin_password(self) -> bool:
        return self.admin_password == DEFAULT_ADMIN_PASSWORD


settings = Settings()
