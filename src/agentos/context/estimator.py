from __future__ import annotations

from collections.abc import Iterable

from agentos.context.schemas import ContextStatus, ContextUsage
from agentos.models.schemas import ActiveModelState

WARN_THRESHOLD = 80.0
CRITICAL_THRESHOLD = 95.0


def estimate_tokens(*parts: str | None, reported_tokens: int | None = None) -> int:
    if reported_tokens is not None:
        return max(0, reported_tokens)
    text = " ".join(part for part in parts if part)
    if not text.strip():
        return 0
    return max(1, (len(text) + 2) // 3)


def estimate_context_usage(
    *,
    model_profile: str,
    context_window_tokens: int,
    input_texts: Iterable[str | None] = (),
    output_texts: Iterable[str | None] = (),
    reserved_output_tokens: int = 0,
    reported_input_tokens: int | None = None,
    reported_output_tokens: int | None = None,
) -> ContextUsage:
    input_tokens = estimate_tokens(*input_texts, reported_tokens=reported_input_tokens)
    output_tokens = estimate_tokens(*output_texts, reported_tokens=reported_output_tokens)
    reserved_tokens = max(0, reserved_output_tokens)
    total = input_tokens + output_tokens + reserved_tokens
    status = _status_for_total(total, context_window_tokens)
    used_percent = None
    if context_window_tokens > 0:
        used_percent = round((total / context_window_tokens) * 100, 2)
    return ContextUsage(
        model_profile=model_profile,
        context_window_tokens=max(0, context_window_tokens),
        estimated_input_tokens=input_tokens,
        estimated_output_tokens=output_tokens,
        reserved_output_tokens=reserved_tokens,
        total_estimated_tokens=total,
        used_percent=used_percent,
        status=status,
    )


def context_usage_from_active_state(active: ActiveModelState) -> ContextUsage:
    return estimate_context_usage(
        model_profile=active.active_model_profile,
        context_window_tokens=active.context_window_tokens,
        reported_input_tokens=active.context_used_tokens,
        reported_output_tokens=0,
    )


def _status_for_total(total_tokens: int, context_window_tokens: int) -> ContextStatus:
    if context_window_tokens <= 0:
        return "unknown"
    used_percent = (total_tokens / context_window_tokens) * 100
    if used_percent >= CRITICAL_THRESHOLD:
        return "critical"
    if used_percent >= WARN_THRESHOLD:
        return "warn"
    return "ok"
