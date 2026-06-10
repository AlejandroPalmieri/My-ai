from agentos.models.config import (
    create_default_model_config,
    inspect_model_status,
    load_model_config,
    reset_usage,
    set_active_model_profile,
)
from agentos.models.pricing import estimate_cost_usd, format_estimated_cost
from agentos.models.registry import ModelRegistry
from agentos.models.usage import record_usage


def test_models_yaml_creation_has_default_profiles(tmp_path):
    path = create_default_model_config(tmp_path)
    config = load_model_config(tmp_path)

    assert path == tmp_path / ".agentos" / "models.yaml"
    assert path.exists()
    assert config.active.active_model_profile == "local-stub"
    assert {profile.name for profile in config.model_profiles} == {
        "local-stub",
        "openai-gpt-5-5-thinking",
        "openai-gpt-5-5",
        "openrouter-auto",
        "ollama-local",
    }
    assert "OPENAI_API_KEY" in path.read_text(encoding="utf-8")
    assert "sk-" not in path.read_text(encoding="utf-8")


def test_registry_lists_and_sets_model_profile(tmp_path):
    create_default_model_config(tmp_path)
    registry = ModelRegistry(tmp_path)

    enabled_profiles = registry.enabled_profiles()
    updated = set_active_model_profile(tmp_path, "ollama-local")

    assert "local-stub" in [profile.name for profile in enabled_profiles]
    assert updated.active.active_model_profile == "ollama-local"
    assert updated.active.active_provider == "ollama"
    assert updated.active.active_model == "local"
    assert updated.active.effort == "low"


def test_usage_calculation_updates_active_state(tmp_path):
    create_default_model_config(tmp_path)
    set_active_model_profile(tmp_path, "local-stub")

    updated = record_usage(tmp_path, input_tokens=120, output_tokens=30)

    assert updated.active.context_used_tokens == 150
    assert updated.active.context_used_percent == 1.5
    assert updated.active.cumulative_input_tokens == 120
    assert updated.active.cumulative_output_tokens == 30
    assert updated.active.cumulative_total_tokens == 150
    assert updated.active.cumulative_estimated_cost_usd == 0.0
    assert estimate_cost_usd(1000, 1000, None, 1.0) is None
    assert format_estimated_cost(None) == "n/a"


def test_reset_usage_requires_confirm(tmp_path):
    create_default_model_config(tmp_path)
    record_usage(tmp_path, input_tokens=10, output_tokens=5)

    try:
        reset_usage(tmp_path, confirm=False)
    except ValueError as error:
        assert "--confirm" in str(error)
    else:
        raise AssertionError("reset_usage should require confirmation")

    reset = reset_usage(tmp_path, confirm=True)

    assert reset.active.cumulative_total_tokens == 0
    assert reset.active.context_used_tokens == 0
    assert "cumulative_total_tokens" in (
        tmp_path / ".agentos" / "model-usage.json"
    ).read_text(encoding="utf-8")


def test_missing_api_key_is_warning_not_crash(tmp_path, monkeypatch):
    create_default_model_config(tmp_path)
    set_active_model_profile(tmp_path, "openai-gpt-5-5")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    status = inspect_model_status(tmp_path)

    assert status.status == "not configured"
    assert status.active_model_profile == "openai-gpt-5-5"
    assert status.api_key_env == "OPENAI_API_KEY"
    assert status.warnings


def test_local_stub_is_configured_without_api_key(tmp_path):
    create_default_model_config(tmp_path)

    status = inspect_model_status(tmp_path)

    assert status.status == "configured"
    assert status.provider_kind == "local_stub"
    assert status.api_key_env is None
    assert status.warnings == []
