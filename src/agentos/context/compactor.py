from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from agentos.context.estimator import estimate_context_usage
from agentos.context.schemas import CompactionResult, ContextMessage


def compact_session_history(
    messages: Sequence[Any],
    *,
    model_profile: str,
    context_window_tokens: int,
    system_prompt: str | None = None,
    latest_message: str | None = None,
    reserved_output_tokens: int = 0,
    max_used_percent: float = 95.0,
) -> CompactionResult:
    kept = [_to_context_message(message) for message in messages]
    usage = _estimate(
        kept,
        model_profile=model_profile,
        context_window_tokens=context_window_tokens,
        system_prompt=system_prompt,
        latest_message=latest_message,
        reserved_output_tokens=reserved_output_tokens,
    )
    dropped = 0
    while (
        usage.used_percent is not None
        and usage.used_percent > max_used_percent
        and kept
    ):
        kept.pop(0)
        dropped += 1
        usage = _estimate(
            kept,
            model_profile=model_profile,
            context_window_tokens=context_window_tokens,
            system_prompt=system_prompt,
            latest_message=latest_message,
            reserved_output_tokens=reserved_output_tokens,
        )
    notice = None
    if dropped:
        notice = f"Context compacted: dropped {dropped} oldest message(s)."
    return CompactionResult(
        messages=kept,
        dropped_count=dropped,
        notice=notice,
        usage=usage,
    )


def _estimate(
    messages: list[ContextMessage],
    *,
    model_profile: str,
    context_window_tokens: int,
    system_prompt: str | None,
    latest_message: str | None,
    reserved_output_tokens: int,
):
    return estimate_context_usage(
        model_profile=model_profile,
        context_window_tokens=context_window_tokens,
        input_texts=[
            system_prompt,
            *(message.content for message in messages),
            latest_message,
        ],
        reserved_output_tokens=reserved_output_tokens,
    )


def _to_context_message(message: Any) -> ContextMessage:
    if isinstance(message, ContextMessage):
        return message
    if isinstance(message, dict):
        return ContextMessage(
            role=str(message.get("role") or "message"),
            content=str(message.get("content") or ""),
        )
    return ContextMessage(
        role=str(getattr(message, "role", "message")),
        content=str(getattr(message, "content", "")),
    )
