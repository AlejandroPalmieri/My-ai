from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from agentos.models.pricing import estimate_cost_usd
from agentos.models.schemas import (
    ActiveModelState,
    ModelConfig,
    ModelProfile,
    ModelProvider,
    ModelProviderStatus,
)


def create_default_model_config(root: Path) -> Path:
    path = model_config_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        write_model_config(path, default_model_config())
    return path


def load_model_config(root: Path) -> ModelConfig:
    path = create_default_model_config(root)
    return read_model_config(path)


def read_model_config(path: Path) -> ModelConfig:
    if not path.exists():
        return default_model_config()
    return _parse_model_config(path.read_text(encoding="utf-8"))


def write_model_config(path: Path, config: ModelConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(_render_model_config(config), encoding="utf-8")
    temp_path.replace(path)


def set_active_model_profile(root: Path, profile_name: str) -> ModelConfig:
    path = create_default_model_config(root)
    config = read_model_config(path)
    profile = _profile_by_name(config, profile_name)
    provider = _provider_by_name(config, profile.provider)
    if not profile.enabled:
        raise ValueError(f"Model profile is disabled: {profile_name}")
    if not provider.enabled:
        raise ValueError(f"Model provider is disabled: {profile.provider}")
    config.active = _active_state_from_profile(profile)
    write_model_config(path, config)
    return config


def inspect_model_status(root: Path) -> ModelProviderStatus:
    config = load_model_config(root)
    profile = _profile_by_name(config, config.active.active_model_profile)
    provider = _provider_by_name(config, profile.provider)
    warnings: list[str] = []
    status = "configured"
    if provider.api_key_env and not os.environ.get(provider.api_key_env):
        status = "not configured"
        warnings.append(f"Missing environment variable: {provider.api_key_env}")
    if provider.kind == "local_stub":
        status = "configured"
        warnings = []
    return ModelProviderStatus(
        active_model_profile=profile.name,
        active_provider=provider.name,
        active_model=profile.model,
        provider_kind=provider.kind,
        status=status,
        api_key_env=provider.api_key_env,
        warnings=warnings,
        usage=config.active,
    )


def reset_usage(root: Path, *, confirm: bool = False) -> ModelConfig:
    if not confirm:
        raise ValueError("Usage reset requires --confirm.")
    path = create_default_model_config(root)
    config = read_model_config(path)
    profile = _profile_by_name(config, config.active.active_model_profile)
    config.active = _active_state_from_profile(profile)
    write_model_config(path, config)
    _write_usage_snapshot(root, config)
    return config


def model_config_path(root: Path) -> Path:
    return root / ".agentos" / "models.yaml"


def _write_usage_snapshot(root: Path, config: ModelConfig) -> None:
    path = root / ".agentos" / "model-usage.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config.active.model_dump(), indent=2) + "\n", encoding="utf-8")


def default_model_config() -> ModelConfig:
    providers = [
        ModelProvider(name="local", kind="local_stub", supports_streaming=True),
        ModelProvider(
            name="openai",
            kind="openai",
            base_url="https://api.openai.com/v1",
            api_key_env="OPENAI_API_KEY",
            supports_streaming=True,
        ),
        ModelProvider(
            name="anthropic",
            kind="anthropic",
            base_url="https://api.anthropic.com/v1",
            api_key_env="ANTHROPIC_API_KEY",
            supports_streaming=True,
        ),
        ModelProvider(
            name="openrouter",
            kind="openrouter",
            base_url="https://openrouter.ai/api/v1",
            api_key_env="OPENROUTER_API_KEY",
            supports_streaming=True,
            extra_headers={"HTTP-Referer": "https://github.com/AlejandroPalmieri/My-ai"},
        ),
        ModelProvider(
            name="ollama",
            kind="ollama",
            base_url="http://localhost:11434/v1",
            supports_streaming=True,
        ),
    ]
    profiles = [
        ModelProfile(
            name="local-stub",
            provider="local",
            model="local-stub",
            effort="low",
            context_window_tokens=10_000,
            input_token_cost_per_1m=0.0,
            output_token_cost_per_1m=0.0,
            default_temperature=0.0,
        ),
        ModelProfile(
            name="openai-gpt-5-5-thinking",
            provider="openai",
            model="gpt-5.5-thinking",
            effort="max",
            context_window_tokens=128_000,
        ),
        ModelProfile(
            name="openai-gpt-5-5",
            provider="openai",
            model="gpt-5.5",
            effort="medium",
            context_window_tokens=128_000,
        ),
        ModelProfile(
            name="openrouter-auto",
            provider="openrouter",
            model="auto",
            effort="medium",
            context_window_tokens=128_000,
        ),
        ModelProfile(
            name="anthropic-claude-sonnet",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            effort="medium",
            context_window_tokens=200_000,
        ),
        ModelProfile(
            name="ollama-local",
            provider="ollama",
            model="local",
            effort="low",
            context_window_tokens=8_192,
            input_token_cost_per_1m=0.0,
            output_token_cost_per_1m=0.0,
        ),
    ]
    return ModelConfig(
        active=_active_state_from_profile(profiles[0]),
        providers=providers,
        model_profiles=profiles,
    )


def _active_state_from_profile(profile: ModelProfile) -> ActiveModelState:
    return ActiveModelState(
        active_model_profile=profile.name,
        active_provider=profile.provider,
        active_model=profile.model,
        effort=profile.effort,
        context_window_tokens=profile.context_window_tokens,
        cumulative_estimated_cost_usd=0.0
        if _pricing_known(profile)
        else None,
    )


def _pricing_known(profile: ModelProfile) -> bool:
    return (
        profile.input_token_cost_per_1m is not None
        and profile.output_token_cost_per_1m is not None
    )


def _profile_by_name(config: ModelConfig, name: str) -> ModelProfile:
    for profile in config.model_profiles:
        if profile.name == name:
            return profile
    raise KeyError(f"Unknown model profile: {name}")


def _provider_by_name(config: ModelConfig, name: str) -> ModelProvider:
    for provider in config.providers:
        if provider.name == name:
            return provider
    raise KeyError(f"Unknown model provider: {name}")


def _render_model_config(config: ModelConfig) -> str:
    lines = ["active:"]
    for key, value in config.active.model_dump().items():
        lines.append(f"  {key}: {_render_scalar(value)}")
    lines.append("providers:")
    for provider in config.providers:
        lines.append(f"  - name: {_render_scalar(provider.name)}")
        for key, value in provider.model_dump().items():
            if key == "name":
                continue
            lines.append(f"    {key}: {_render_scalar(value)}")
    lines.append("model_profiles:")
    for profile in config.model_profiles:
        lines.append(f"  - name: {_render_scalar(profile.name)}")
        for key, value in profile.model_dump().items():
            if key == "name":
                continue
            lines.append(f"    {key}: {_render_scalar(value)}")
    lines.append("")
    return "\n".join(lines)


def _parse_model_config(content: str) -> ModelConfig:
    active: dict[str, Any] = {}
    providers: list[dict[str, Any]] = []
    profiles: list[dict[str, Any]] = []
    section = ""
    current: dict[str, Any] | None = None
    for raw_line in content.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        stripped = raw_line.strip()
        if not raw_line.startswith(" ") and stripped.endswith(":"):
            if current is not None:
                _append_item(section, current, providers, profiles)
                current = None
            section = stripped[:-1]
            continue
        if section == "active" and raw_line.startswith("  ") and ":" in stripped:
            key, value = stripped.split(":", 1)
            active[key.strip()] = _parse_scalar(value.strip())
            continue
        if section in {"providers", "model_profiles"} and raw_line.startswith("  - "):
            if current is not None:
                _append_item(section, current, providers, profiles)
            current = {}
            item = stripped[2:].strip()
            if ":" in item:
                key, value = item.split(":", 1)
                current[key.strip()] = _parse_scalar(value.strip())
            continue
        if current is not None and raw_line.startswith("    ") and ":" in stripped:
            key, value = stripped.split(":", 1)
            current[key.strip()] = _parse_scalar(value.strip())
    if current is not None:
        _append_item(section, current, providers, profiles)
    return ModelConfig(
        active=ActiveModelState(**active),
        providers=[ModelProvider(**item) for item in providers],
        model_profiles=[ModelProfile(**item) for item in profiles],
    )


def _append_item(
    section: str,
    item: dict[str, Any],
    providers: list[dict[str, Any]],
    profiles: list[dict[str, Any]],
) -> None:
    if section == "providers":
        providers.append(item)
    elif section == "model_profiles":
        profiles.append(item)


def _render_scalar(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    return str(value)


def _parse_scalar(value: str) -> object:
    normalized = value.strip().strip('"').strip("'")
    if normalized.lower() == "null":
        return None
    if normalized.lower() == "true":
        return True
    if normalized.lower() == "false":
        return False
    if normalized.startswith("{") and normalized.endswith("}"):
        try:
            return json.loads(normalized)
        except json.JSONDecodeError:
            return {}
    try:
        return int(normalized)
    except ValueError:
        pass
    try:
        return float(normalized)
    except ValueError:
        return normalized


def update_active_usage(
    config: ModelConfig,
    *,
    input_tokens: int,
    output_tokens: int,
) -> ModelConfig:
    profile = _profile_by_name(config, config.active.active_model_profile)
    active = config.active.model_copy(deep=True)
    active.context_used_tokens += input_tokens + output_tokens
    if active.context_window_tokens:
        active.context_used_percent = round(
            (active.context_used_tokens / active.context_window_tokens) * 100,
            2,
        )
    active.cumulative_input_tokens += input_tokens
    active.cumulative_output_tokens += output_tokens
    active.cumulative_total_tokens += input_tokens + output_tokens
    current_cost = active.cumulative_estimated_cost_usd
    usage_cost = estimate_cost_usd(
        input_tokens,
        output_tokens,
        profile.input_token_cost_per_1m,
        profile.output_token_cost_per_1m,
    )
    if current_cost is None or usage_cost is None:
        active.cumulative_estimated_cost_usd = None
    else:
        active.cumulative_estimated_cost_usd = round(current_cost + usage_cost, 8)
    config.active = active
    return config
