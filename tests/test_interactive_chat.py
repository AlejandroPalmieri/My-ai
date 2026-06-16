from datetime import UTC, datetime

from agentos.agents.registry import AgentRuntimeRegistry
from agentos.cli.interactive_chat import (
    InteractiveChatSession,
    parse_interactive_command,
)
from agentos.memory.store import MemoryStore
from agentos.models.config import create_default_model_config, load_model_config


def test_interactive_command_parser():
    assert parse_interactive_command("help").name == "help"
    assert parse_interactive_command("exit").name == "exit"
    assert parse_interactive_command("/model list").name == "model.list"
    assert parse_interactive_command("/model set local-stub").args == ["local-stub"]
    assert parse_interactive_command("/effort high").name == "effort"
    assert parse_interactive_command("/stream on").name == "stream.on"
    assert parse_interactive_command("/stream off").name == "stream.off"
    assert parse_interactive_command("/stream status").name == "stream.status"
    assert parse_interactive_command("/memory search SQLite").args == ["SQLite"]
    assert parse_interactive_command("hello agentos").name == "message"


def test_model_list_and_set(tmp_path):
    create_default_model_config(tmp_path)
    session = InteractiveChatSession(tmp_path)

    listed = session.handle_input("/model list")
    updated = session.handle_input("/model set ollama-local")

    assert listed.should_exit is False
    assert "local-stub" in listed.output
    assert "ollama-local" in listed.output
    assert "Active model profile set to ollama-local" in updated.output
    assert load_model_config(tmp_path).active.active_model_profile == "ollama-local"


def test_normal_message_uses_local_stub_and_updates_usage(tmp_path):
    session = InteractiveChatSession(tmp_path)

    result = session.handle_input("Hello interactive AgentOS")
    usage = load_model_config(tmp_path).active

    assert result.should_exit is False
    assert "local-stub response" in result.output
    assert "Hello interactive AgentOS" in result.output
    assert usage.cumulative_total_tokens > 0
    assert usage.context_used_percent > 0
    assert session.history[-2].role == "user"
    assert session.history[-1].role == "assistant"


def test_usage_and_clear_commands(tmp_path):
    session = InteractiveChatSession(tmp_path)
    session.handle_input("Track usage")

    usage = session.handle_input("/usage")
    cleared = session.handle_input("/clear")
    reset_rejected = session.handle_input("/usage reset")
    reset_accepted = session.handle_input("/usage reset --confirm")

    assert "cumulative_total_tokens" in usage.output
    assert "Session history cleared" in cleared.output
    assert session.history == []
    assert "--confirm" in reset_rejected.output
    assert "Usage reset" in reset_accepted.output


def test_stream_commands_and_default_streaming(tmp_path):
    chunks: list[str] = []
    session = InteractiveChatSession(tmp_path, stream_writer=chunks.append)

    status = session.handle_input("/stream status")
    streamed = session.handle_input("Hello streamed interactive")
    off = session.handle_input("/stream off")
    non_streamed = session.handle_input("Hello non streamed interactive")

    assert "stream=on" in status.output
    assert "".join(chunks)
    assert streamed.output == ""
    assert "Streaming disabled" in off.output
    assert "Hello non streamed interactive" in non_streamed.output


def test_context_warning_and_compaction(tmp_path):
    create_default_model_config(tmp_path)
    session = InteractiveChatSession(
        tmp_path,
        max_history_messages=2,
        system_prompt="system " * 6000,
    )

    warning = session.handle_input("first message")
    compacted = session.handle_input("second message")

    assert "Context usage warning" in warning.output
    assert "Context compacted" in compacted.output
    assert len(session.history) <= 2


def test_memory_search_command_does_not_add_results_to_chat_history(tmp_path):
    MemoryStore(tmp_path).add_memory(
        project="default",
        title="Secret-ish note",
        kind="note",
        content="memory content should not be sent automatically",
        tags=[],
    )
    session = InteractiveChatSession(tmp_path)

    search = session.handle_input("/memory search Secret-ish")
    response = session.handle_input("only this message")

    assert "Secret-ish note" in search.output
    assert session.history[-2].content == "only this message"
    assert "memory content should not be sent automatically" not in response.output


def test_agents_and_dashboard_commands(tmp_path):
    AgentRuntimeRegistry(tmp_path).start_agent(
        name="Planner",
        role="planning",
        current_task="Plan interactive runtime",
        model_profile="local-stub",
    )
    session = InteractiveChatSession(tmp_path)

    agents = session.handle_input("/agents")
    dashboard = session.handle_input("/dashboard")

    assert "Planner" in agents.output
    assert dashboard.dashboard_requested is True
    assert "Dashboard refreshed" in dashboard.output


def test_interactive_traces_are_written(tmp_path):
    session = InteractiveChatSession(tmp_path)

    session.handle_input("trace interactive")

    trace_path = tmp_path / ".agentos" / "traces" / f"{datetime.now(UTC).date()}.jsonl"
    trace_text = trace_path.read_text(encoding="utf-8")
    assert "interactive_message_sent" in trace_text
    assert "interactive_message_received" in trace_text
    assert "model_request_started" in trace_text
