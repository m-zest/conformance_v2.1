"""Token cost estimation.

Prices are USD per one million tokens and are matched by model name prefix.
The built-in table is a starting point only. Put your contracted prices in a
JSON file and point PRICING_PATH at it:

    {"gpt-4o": {"input": 2.5, "output": 10.0}, "my-internal-model": {"input": 0, "output": 0}}
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from .config import settings

log = logging.getLogger("conformance.pricing")

_DEFAULT = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4.1": {"input": 2.00, "output": 8.00},
    "claude-haiku": {"input": 1.00, "output": 5.00},
    "claude-sonnet": {"input": 3.00, "output": 15.00},
    "claude-opus": {"input": 5.00, "output": 25.00},
    "simulator": {"input": 0.50, "output": 1.50},
}


def _load() -> list[tuple[str, float, float]]:
    table = dict(_DEFAULT)
    if settings.pricing_path:
        try:
            table.update(json.loads(Path(settings.pricing_path).read_text(encoding="utf-8")))
        except Exception as exc:
            log.warning("could not read pricing file %s: %s", settings.pricing_path, exc)
    rows = [(k.lower(), float(v.get("input", 0)), float(v.get("output", 0))) for k, v in table.items()]
    return sorted(rows, key=lambda r: -len(r[0]))  # longest prefix wins


_TABLE = _load()


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    name = (model or "").lower()
    for prefix, price_in, price_out in _TABLE:
        if name.startswith(prefix):
            return round((input_tokens * price_in + output_tokens * price_out) / 1_000_000, 6)
    return 0.0
