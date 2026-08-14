from typing import Dict, Any

class OpenTelemetryGenAIAdapter:
    """
    Implements CNCF OpenTelemetry Semantic Conventions for GenAI (gen_ai.* namespace).
    Provides structured attributes mapping directly to Datadog, Prometheus, Grafana, and ClickHouse.
    """

    MODEL_COST_PER_1K_TOKENS = {
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
        "local-mistral-7b": {"input": 0.0001, "output": 0.0001},
        "phi4-mini-local": {"input": 0.00005, "output": 0.00005},
        "gemma-3-4b": {"input": 0.00005, "output": 0.00005},
    }

    def estimate_tokens(self, text: str) -> int:
        # Fast local token estimation (~4 chars per token)
        return max(1, len(text.strip()) // 4)

    def calculate_cost(self, model: str, in_tokens: int, out_tokens: int) -> float:
        rates = self.MODEL_COST_PER_1K_TOKENS.get(model, {"input": 0.002, "output": 0.005})
        cost = (in_tokens / 1000.0) * rates["input"] + (out_tokens / 1000.0) * rates["output"]
        return round(cost, 6)

    def generate_otel_attributes(
        self,
        request_model: str,
        response_model: str,
        provider_name: str,
        input_text: str,
        output_text: str,
        operation_name: str = "chat"
    ) -> Dict[str, Any]:
        in_tokens = self.estimate_tokens(input_text)
        out_tokens = self.estimate_tokens(output_text)
        cost = self.calculate_cost(response_model, in_tokens, out_tokens)

        return {
            "gen_ai.system": "openai-compatible",
            "gen_ai.provider.name": provider_name,
            "gen_ai.request.model": request_model,
            "gen_ai.response.model": response_model,
            "gen_ai.operation.name": operation_name,
            "gen_ai.usage.input_tokens": in_tokens,
            "gen_ai.usage.output_tokens": out_tokens,
            "gen_ai.usage.total_tokens": in_tokens + out_tokens,
            "gen_ai.cost.usd": cost,
            "gen_ai.compliance.standard": "OTEL-SEMCONV-1.44.0"
        }

otel_adapter = OpenTelemetryGenAIAdapter()
