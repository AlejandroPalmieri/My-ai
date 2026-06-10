from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from agentos.config.profiles import load_project_profile
from agentos.models.config import (
    create_default_model_config,
    read_model_config,
    update_active_usage,
    write_model_config,
)
from agentos.models.pricing import estimate_cost_usd
from agentos.models.schemas import ChatUsage, ModelConfig, ModelProfile
from agentos.usage.schemas import UsageEvent
from agentos.usage.store import UsageStore


def record_usage(root: Path, *, input_tokens: int, output_tokens: int) -> ModelConfig:
    updated, _ = record_model_usage(
        root,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    return updated


def record_model_usage(
    root: Path,
    *,
    input_tokens: int,
    output_tokens: int,
    provider: str | None = None,
    model: str | None = None,
    effort: str | None = None,
    command: str = "model.usage",
    session_id: str | None = None,
    agent_id: str | None = None,
) -> tuple[ModelConfig, UsageEvent | None]:
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("Token counts must be non-negative.")
    path = create_default_model_config(root)
    config = read_model_config(path)
    updated = update_active_usage(
        config,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    write_model_config(path, updated)
    _write_usage_store(root, updated)
    usage_event = _write_usage_event(
        root,
        updated,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        provider=provider or updated.active.active_provider,
        model=model or updated.active.active_model,
        effort=effort or updated.active.effort,
        command=command,
        session_id=session_id or uuid4().hex,
        agent_id=agent_id,
    )
    return updated, usage_event


def chat_usage_for_profile(
    profile: ModelProfile,
    *,
    input_tokens: int,
    output_tokens: int,
) -> ChatUsage:
    return ChatUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        estimated_cost_usd=estimate_cost_usd(
            input_tokens,
            output_tokens,
            profile.input_token_cost_per_1m,
            profile.output_token_cost_per_1m,
        ),
    )


def _write_usage_store(root: Path, config: ModelConfig) -> None:
    path = root / ".agentos" / "model-usage.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    active = config.active
    payload = {
        "active_model_profile": active.active_model_profile,
        "active_provider": active.active_provider,
        "active_model": active.active_model,
        "effort": active.effort,
        "context_window_tokens": active.context_window_tokens,
        "context_used_tokens": active.context_used_tokens,
        "context_used_percent": active.context_used_percent,
        "cumulative_input_tokens": active.cumulative_input_tokens,
        "cumulative_output_tokens": active.cumulative_output_tokens,
        "cumulative_total_tokens": active.cumulative_total_tokens,
        "cumulative_estimated_cost_usd": active.cumulative_estimated_cost_usd,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_usage_event(
    root: Path,
    config: ModelConfig,
    *,
    input_tokens: int,
    output_tokens: int,
    provider: str,
    model: str,
    effort: str,
    command: str,
    session_id: str,
    agent_id: str | None,
) -> UsageEvent:
    profile = load_project_profile(root)
    usage_cost = estimate_cost_usd(
        input_tokens,
        output_tokens,
        _active_profile(config).input_token_cost_per_1m,
        _active_profile(config).output_token_cost_per_1m,
    )
    return UsageStore(root).record_event(
        session_id=session_id,
        project=profile.active.default_project,
        profile=profile.active_profile,
        provider=provider,
        model=model,
        effort=effort,
        agent_id=agent_id,
        command=command,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=usage_cost,
        context_used_percent=config.active.context_used_percent,
    )


def _active_profile(config: ModelConfig) -> ModelProfile:
    for profile in config.model_profiles:
        if profile.name == config.active.active_model_profile:
            return profile
    raise KeyError(f"Unknown model profile: {config.active.active_model_profile}")
