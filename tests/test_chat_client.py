import json
from datetime import UTC, datetime

from agentos.models.client import chat_once
from agentos.models.config import (
    create_default_model_config,
    read_model_config,
    set_active_model_profile,
    write_model_config,
)
from agentos.models.providers.local_stub import LocalStubProvider
from agentos.models.schemas import ChatRequest
from agentos.usage.store import UsageStore


def test_local_stub_chat_once_returns_deterministic_response_and_updates_usage(tmp_path):
    create_default_model_config(tmp_path)

    response = chat_once(tmp_path, message="Hello AgentOS", system_prompt="Be brief")

    assert response.provider == "local"
    assert response.model_profile == "local-stub"
    assert "local-stub response" in response.text
    assert "Hello AgentOS" in response.text
    assert response.usage.input_tokens > 0
    assert response.usage.output_tokens > 0
    usage_path = tmp_path / ".agentos" / "model-usage.json"
    usage = json.loads(usage_path.read_text(encoding="utf-8"))
    assert usage["cumulative_total_tokens"] == response.usage.total_tokens


def test_chat_once_override_model_and_effort(tmp_path):
    create_default_model_config(tmp_path)

    response = chat_once(
        tmp_path,
        message="Use override",
        model_profile_name="local-stub",
        effort="high",
    )

    assert response.model_profile == "local-stub"
    assert response.effort == "high"


def test_missing_openai_compatible_api_key_returns_setup_guidance(tmp_path, monkeypatch):
    create_default_model_config(tmp_path)
    set_active_model_profile(tmp_path, "openrouter-auto")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    response = chat_once(tmp_path, message="hello")

    assert response.status == "not configured"
    assert "OPENROUTER_API_KEY" in response.text
    assert response.usage.total_tokens == 0


def test_chat_once_writes_model_trace_events_without_secret_values(tmp_path, monkeypatch):
    create_default_model_config(tmp_path)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-secret-value")

    response = chat_once(tmp_path, message="trace test")

    assert response.status == "ok"
    trace_path = tmp_path / ".agentos" / "traces" / f"{datetime.now(UTC).date()}.jsonl"
    trace_text = trace_path.read_text(encoding="utf-8")
    assert "model_request_started" in trace_text
    assert "model_request_completed" in trace_text
    assert "model_usage_updated" in trace_text
    assert "usage_event_id" in trace_text
    assert "sk-test-secret-value" not in trace_text


def test_chat_once_does_not_send_implicit_local_context(tmp_path):
    create_default_model_config(tmp_path)
    secret_file = tmp_path / "notes.txt"
    secret_file.write_text("should not be sent automatically", encoding="utf-8")

    response = chat_once(tmp_path, message="only this message")

    assert "only this message" in response.text
    assert "should not be sent automatically" not in response.text


def test_local_stub_streaming_returns_deterministic_chunks(tmp_path):
    config_path = create_default_model_config(tmp_path)
    config = read_model_config(config_path)
    provider = config.providers[0]
    profile = config.model_profiles[0]

    events = list(
        LocalStubProvider().stream(
            ChatRequest(message="hello streaming", model_profile_name="local-stub"),
            provider,
            profile,
        )
    )

    assert events[0].type == "message_start"
    assert events[-1].type == "message_done"
    assert "local-stub response" in "".join(event.delta for event in events)
    assert any(event.type == "usage_delta" for event in events)


def test_chat_once_stream_updates_usage_and_traces_without_prompt_body(tmp_path):
    create_default_model_config(tmp_path)
    deltas: list[str] = []

    response = chat_once(
        tmp_path,
        message="private prompt body",
        stream=True,
        on_delta=deltas.append,
    )

    trace_path = tmp_path / ".agentos" / "traces" / f"{datetime.now(UTC).date()}.jsonl"
    trace_text = trace_path.read_text(encoding="utf-8")
    usage_events = UsageStore(tmp_path).events()

    assert response.status == "ok"
    assert response.streamed is True
    assert "".join(deltas) == response.text
    assert usage_events[-1].total_tokens == response.usage.total_tokens
    assert "stream_started" in trace_text
    assert "stream_delta_received" in trace_text
    assert "stream_completed" in trace_text
    assert "private prompt body" not in trace_text
    assert all("private prompt body" not in event.model_dump_json() for event in usage_events)


def test_chat_once_stream_falls_back_when_provider_does_not_support_streaming(tmp_path):
    path = create_default_model_config(tmp_path)
    config = read_model_config(path)
    config.providers[0].supports_streaming = False
    config.providers[0].kind = "ollama"
    write_model_config(path, config)

    response = chat_once(tmp_path, message="fallback", stream=True)

    assert response.stream_fallback is True
    assert response.streamed is False
