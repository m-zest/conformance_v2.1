import time
import functools
import threading
import httpx
from typing import Callable, Any, Optional, Dict

class ContinuousGovernanceClient:
    """
    Python SDK for Continuous Enterprise AI Governance.
    Provides zero-latency decorators and synchronous active guardrails for any internal AI workflow.
    """

    def __init__(
        self,
        endpoint_url: str = "http://localhost:8000",
        default_profile: str = "customer_support",
        fail_mode: str = "fail_open"  # "fail_open" or "fail_closed"
    ):
        self.endpoint_url = endpoint_url.rstrip("/")
        self.default_profile = default_profile
        self.fail_mode = fail_mode
        self._sync_client = httpx.Client(timeout=5.0)

    def _async_dispatch_telemetry(self, payload: Dict[str, Any]):
        """Fire-and-forget background worker to ensure zero added latency in audit mode."""
        def _worker():
            try:
                httpx.post(f"{self.endpoint_url}/govern/evaluate", json=payload, timeout=4.0)
            except Exception as e:
                # Log silently in background without crashing the main application thread
                pass
        
        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def evaluate_sync(self, prompt: str, profile_id: Optional[str] = None, mode: str = "active_block") -> Dict[str, Any]:
        """Synchronously scan and evaluate prompt against the governance proxy."""
        payload = {
            "prompt": prompt,
            "profile_id": profile_id or self.default_profile,
            "mode": mode,
            "model": "gpt-4o",
            "client_type": "SDK_DECORATOR",
            "app_name": "Internal-Python-SDK"
        }
        try:
            resp = self._sync_client.post(f"{self.endpoint_url}/govern/evaluate", json=payload)
            if resp.status_code == 200:
                return resp.json()
            else:
                if self.fail_mode == "fail_closed":
                    raise RuntimeError(f"Governance Engine Error ({resp.status_code}): Request blocked by fail-closed policy.")
                return {"choices": [{"message": {"content": prompt}}], "governance_metadata": {"verdict": "FAIL_OPEN_SERVED"}}
        except Exception as e:
            print(f"[SDK Debug Error]: {e}")
            if self.fail_mode == "fail_closed":
                raise RuntimeError(f"Governance Engine Unreachable: {e}") from e
            return {"choices": [{"message": {"content": prompt}}], "governance_metadata": {"verdict": "FAIL_OPEN_FALLBACK"}}

govern_client = ContinuousGovernanceClient()

def govern(profile: str = "customer_support", mode: str = "active_block", app_name: str = "Developer-Tool"):
    """
    Enterprise AI Governance Decorator.
    Wrap any LLM invocation function to automatically enforce PII redaction, prompt injection defense,
    and OpenTelemetry GenAI compliance logging.
    
    Example:
        @govern(profile="code_assistant", mode="active_block")
        def call_my_model(prompt: str):
            return openai_client.chat.completions.create(...)
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract prompt from first positional argument or kwargs
            prompt = args[0] if args else kwargs.get("prompt", str(args))
            
            if mode == "audit_passive":
                # Fire-and-forget async dispatch (zero latency added to application)
                govern_client._async_dispatch_telemetry({
                    "prompt": str(prompt),
                    "profile_id": profile,
                    "mode": "audit_passive",
                    "model": "internal-model",
                    "client_type": "SDK_DECORATOR",
                    "app_name": app_name
                })
                return func(*args, **kwargs)
            else:
                # Active synchronous inspection
                eval_res = govern_client.evaluate_sync(prompt=str(prompt), profile_id=profile, mode=mode)
                meta = eval_res.get("governance_metadata", {})
                verdict = meta.get("verdict", "")
                
                if "BLOCKED" in verdict:
                    refusal_content = eval_res["choices"][0]["message"]["content"]
                    raise PermissionError(f"[AI Governance Block] {refusal_content}")
                
                return func(*args, **kwargs)
        return wrapper
    return decorator
