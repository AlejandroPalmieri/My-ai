from __future__ import annotations


def estimate_cost_usd(
    input_tokens: int,
    output_tokens: int,
    input_token_cost_per_1m: float | None,
    output_token_cost_per_1m: float | None,
) -> float | None:
    if input_token_cost_per_1m is None or output_token_cost_per_1m is None:
        return None
    input_cost = (input_tokens / 1_000_000) * input_token_cost_per_1m
    output_cost = (output_tokens / 1_000_000) * output_token_cost_per_1m
    return round(input_cost + output_cost, 8)


def format_estimated_cost(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"${value:.6f}"
