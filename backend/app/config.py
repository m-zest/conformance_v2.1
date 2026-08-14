import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

class Settings:
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DB_PATH: str = str(DATA_DIR / "governance_vault.db")
    
    # Upstream AI Provider (can point to Ollama, vLLM, local simulator, or external)
    UPSTREAM_BASE_URL: str = os.getenv("UPSTREAM_BASE_URL", "http://localhost:11434/v1")
    UPSTREAM_API_KEY: str = os.getenv("UPSTREAM_API_KEY", "local-token")
    
    # Master Signing Secret for Cryptographic Hash Chains & Signatures
    HMAC_SECRET: str = os.getenv("HMAC_SECRET", "enterprise-gov-master-key-2026-secure")
    
    # Fallback simulation mode enabled when on-prem Ollama is not active
    ENABLE_LOCAL_SLM_SIMULATION: bool = True
    
    # Latency simulation targets (realistic on-prem CPU bounds)
    TARGET_DETERMINISTIC_LATENCY_MS: float = 12.0
    TARGET_JURY_LATENCY_MS: float = 45.0

settings = Settings()
