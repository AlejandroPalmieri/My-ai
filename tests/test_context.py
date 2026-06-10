from agentos.context.compactor import compact_session_history
from agentos.context.estimator import estimate_context_usage, estimate_tokens
from agentos.context.schemas import ContextMessage


def test_conservative_token_estimation():
    assert estimate_tokens("abc") == 1
    assert estimate_tokens("abcd") == 2
    assert estimate_tokens("hello world") >= 4
    assert estimate_tokens("", None) == 0


def test_provider_reported_tokens_are_used_when_available():
    usage = estimate_context_usage(
        model_profile="local-stub",
        context_window_tokens=1000,
        input_texts=["this text would otherwise be estimated"],
        output_texts=["same"],
        reported_input_tokens=123,
        reported_output_tokens=45,
        reserved_output_tokens=10,
    )

    assert usage.estimated_input_tokens == 123
    assert usage.estimated_output_tokens == 45
    assert usage.total_estimated_tokens == 178
    assert usage.used_percent == 17.8
    assert usage.status == "ok"


def test_unknown_context_window():
    usage = estimate_context_usage(
        model_profile="unknown-window",
        context_window_tokens=0,
        input_texts=["prompt"],
        output_texts=[],
    )

    assert usage.status == "unknown"
    assert usage.used_percent is None
    assert usage.context_window_tokens == 0


def test_warn_threshold():
    usage = estimate_context_usage(
        model_profile="warn-model",
        context_window_tokens=100,
        input_texts=[],
        output_texts=[],
        reported_input_tokens=70,
        reported_output_tokens=10,
    )

    assert usage.used_percent == 80.0
    assert usage.status == "warn"


def test_critical_threshold():
    usage = estimate_context_usage(
        model_profile="critical-model",
        context_window_tokens=100,
        input_texts=[],
        output_texts=[],
        reported_input_tokens=90,
        reported_output_tokens=5,
    )

    assert usage.used_percent == 95.0
    assert usage.status == "critical"


def test_compactor_drops_oldest_messages_when_needed():
    messages = [
        ContextMessage(role="user", content="oldest " * 100),
        ContextMessage(role="assistant", content="middle " * 100),
        ContextMessage(role="user", content="latest"),
    ]

    result = compact_session_history(
        messages,
        model_profile="local-stub",
        context_window_tokens=80,
        latest_message="new request",
        reserved_output_tokens=0,
        max_used_percent=80.0,
    )

    assert result.dropped_count > 0
    assert result.messages[0].content != messages[0].content
    assert "Context compacted" in result.notice
    assert result.usage.used_percent is not None
    assert result.usage.used_percent <= 80.0
