from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

_MILLION = Decimal("1000000")
_COST_QUANT = Decimal("0.00000001")

_OPENAI_PROVIDER_NAMES = {
    "openai_api",
    "openai_api_key",
    "openai_codex_oauth",
    "openai_dev_fallback",
}

_MODEL_ALIASES = {
    "gpt-5.4": "gpt-5.4",
    "gpt-5.4-mini": "gpt-5.4-mini",
    "gpt-5.4-nano": "gpt-5.4-nano",
    "gpt-5.5": "gpt-5.5",
    "gpt-5.2": "gpt-5.2",
    "gpt-5.2-chat-latest": "gpt-5.2",
    "gpt-5.2-codex": "gpt-5.2",
    "gpt-5.1": "gpt-5.1",
    "gpt-5.1-chat-latest": "gpt-5.1",
    "gpt-5.1-codex": "gpt-5.1",
    "gpt-5.1-codex-max": "gpt-5.1",
    "gpt-5": "gpt-5",
    "gpt-5-chat-latest": "gpt-5",
    "gpt-5-codex": "gpt-5",
    "gpt-5-mini": "gpt-5-mini",
    "gpt-5-nano": "gpt-5-nano",
    "gpt-4.1": "gpt-4.1",
    "gpt-4.1-mini": "gpt-4.1-mini",
    "gpt-4.1-nano": "gpt-4.1-nano",
    "gpt-4o": "gpt-4o",
    "gpt-4o-mini": "gpt-4o-mini",
}

_PRICES_PER_MILLION = {
    "gpt-5.5": {"input": Decimal("5.00"), "cached_input": Decimal("0.50"), "output": Decimal("30.00")},
    "gpt-5.4": {"input": Decimal("2.50"), "cached_input": Decimal("0.25"), "output": Decimal("15.00")},
    "gpt-5.4-mini": {"input": Decimal("0.75"), "cached_input": Decimal("0.075"), "output": Decimal("4.50")},
    "gpt-5.4-nano": {"input": Decimal("0.20"), "cached_input": Decimal("0.02"), "output": Decimal("1.25")},
    "gpt-5.2": {"input": Decimal("1.75"), "cached_input": Decimal("0.175"), "output": Decimal("14.00")},
    "gpt-5.1": {"input": Decimal("1.25"), "cached_input": Decimal("0.125"), "output": Decimal("10.00")},
    "gpt-5": {"input": Decimal("1.25"), "cached_input": Decimal("0.125"), "output": Decimal("10.00")},
    "gpt-5-mini": {"input": Decimal("0.25"), "cached_input": Decimal("0.025"), "output": Decimal("2.00")},
    "gpt-5-nano": {"input": Decimal("0.05"), "cached_input": Decimal("0.005"), "output": Decimal("0.40")},
    "gpt-4.1": {"input": Decimal("2.00"), "cached_input": Decimal("0.50"), "output": Decimal("8.00")},
    "gpt-4.1-mini": {"input": Decimal("0.40"), "cached_input": Decimal("0.10"), "output": Decimal("1.60")},
    "gpt-4.1-nano": {"input": Decimal("0.10"), "cached_input": Decimal("0.025"), "output": Decimal("0.40")},
    "gpt-4o": {"input": Decimal("2.50"), "cached_input": Decimal("1.25"), "output": Decimal("10.00")},
    "gpt-4o-mini": {"input": Decimal("0.15"), "cached_input": Decimal("0.075"), "output": Decimal("0.60")},
}


def estimate_openai_usage_cost_usd(
    *,
    provider_name: str,
    model: str,
    input_tokens: int | None,
    output_tokens: int | None,
    cached_input_tokens: int | None,
) -> Decimal | None:
    if provider_name.strip() not in _OPENAI_PROVIDER_NAMES:
        return None
    pricing = _PRICES_PER_MILLION.get(_normalize_model(model))
    if pricing is None:
        return None

    cached_tokens = max(cached_input_tokens or 0, 0)
    total_input_tokens = max(input_tokens or 0, 0)
    billable_uncached_input = max(total_input_tokens - cached_tokens, 0)
    output = max(output_tokens or 0, 0)

    cost = (
        Decimal(billable_uncached_input) * pricing["input"]
        + Decimal(cached_tokens) * pricing["cached_input"]
        + Decimal(output) * pricing["output"]
    ) / _MILLION
    return cost.quantize(_COST_QUANT, rounding=ROUND_HALF_UP)


def decimal_to_json_number(value: Decimal) -> float:
    return float(value)


def _normalize_model(model: str) -> str:
    text = str(model or "").strip().lower()
    if text in _MODEL_ALIASES:
        return _MODEL_ALIASES[text]
    for prefix, canonical in sorted(_MODEL_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if text.startswith(f"{prefix}-"):
            return canonical
    return text
