from datetime import UTC, datetime

from typer.testing import CliRunner

from agentos.brain.store import StrategicBrainStore
from agentos.cli.app import app
from agentos.cli.interactive_chat import InteractiveChatSession
from agentos.memory.store import MemoryStore
from agentos.models.client import chat_once
from agentos.retrieval.context_builder import build_retrieval_context
from agentos.retrieval.schemas import RetrievalSettings

runner = CliRunner()


def test_default_chat_does_not_include_memory_or_brain(tmp_path):
    MemoryStore(tmp_path).add_memory(
        project="default",
        title="Hidden memory",
        kind="note",
        content="retrieved memory should not appear",
        tags=[],
    )

    response = chat_once(tmp_path, message="hello")

    assert "retrieved memory should not appear" not in response.text


def test_with_memory_retrieves_memory(tmp_path):
    MemoryStore(tmp_path).add_memory(
        project="default",
        title="Architecture note",
        kind="decision",
        content="Use explicit retrieval only.",
        tags=[],
    )

    response = chat_once(
        tmp_path,
        message="retrieval",
        retrieval_settings=RetrievalSettings(with_memory=True, memory_query="explicit"),
    )

    assert "LOCAL OPT-IN CONTEXT" in response.text
    assert "Use explicit retrieval only" in response.text


def test_with_brain_retrieves_brain_chunks(tmp_path):
    source = tmp_path / "strategy.md"
    source.write_text("# Strategy\n\nRetrieval should cite strategic chunks.", encoding="utf-8")
    StrategicBrainStore(tmp_path).ingest_document(source)

    response = chat_once(
        tmp_path,
        message="strategy",
        retrieval_settings=RetrievalSettings(with_brain=True, brain_query="strategic"),
    )

    assert "Strategic Brain" in response.text
    assert "Retrieval should cite strategic chunks" in response.text


def test_dry_run_context_does_not_call_provider(tmp_path):
    MemoryStore(tmp_path).add_memory(
        project="default",
        title="Dry run",
        kind="note",
        content="Only context should print.",
        tags=[],
    )

    result = runner.invoke(
        app,
        [
            "chat",
            "once",
            "dry",
            "--with-memory",
            "--dry-run-context",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "LOCAL OPT-IN CONTEXT" in result.output
    assert "local-stub response" not in result.output


def test_show_context_prints_context(tmp_path):
    MemoryStore(tmp_path).add_memory(
        project="default",
        title="Show context",
        kind="note",
        content="Show this context.",
        tags=[],
    )

    result = runner.invoke(
        app,
        [
            "chat",
            "once",
            "show",
            "--with-memory",
            "--show-context",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "LOCAL OPT-IN CONTEXT" in result.output
    assert "local-stub response" in result.output


def test_interactive_memory_on_applies_only_to_session(tmp_path):
    MemoryStore(tmp_path).add_memory(
        project="default",
        title="Session memory",
        kind="note",
        content="Session-scoped retrieval.",
        tags=[],
    )
    session = InteractiveChatSession(tmp_path)
    other_session = InteractiveChatSession(tmp_path)

    enabled = session.handle_input("/memory on")
    response = session.handle_input("Session")
    status = other_session.handle_input("/context status")

    assert "enabled" in enabled.output
    assert "Session-scoped retrieval" in response.output
    assert "memory=off" in status.output


def test_context_builder_respects_limits(tmp_path):
    store = MemoryStore(tmp_path)
    for index in range(3):
        store.add_memory(
            project="default",
            title=f"Memory {index}",
            kind="note",
            content="limit-test content",
            tags=[],
        )

    context = build_retrieval_context(
        tmp_path,
        "limit-test",
        RetrievalSettings(with_memory=True, memory_limit=2),
    )

    assert len(context.memory_items) == 2


def test_sensitive_content_is_not_retrieved_automatically(tmp_path):
    MemoryStore(tmp_path).add_memory(
        project="default",
        title=".env secret",
        kind="note",
        content="api_key=secret should stay out",
        tags=[],
    )

    context = build_retrieval_context(
        tmp_path,
        "secret",
        RetrievalSettings(with_memory=True),
    )

    assert not context.memory_items
    assert "api_key=secret" not in context.block


def test_retrieval_traces_do_not_store_full_context_body(tmp_path):
    MemoryStore(tmp_path).add_memory(
        project="default",
        title="Trace memory",
        kind="note",
        content="trace context body must not be logged",
        tags=[],
    )

    chat_once(
        tmp_path,
        message="trace",
        retrieval_settings=RetrievalSettings(with_memory=True, memory_query="trace"),
    )

    trace_path = tmp_path / ".agentos" / "traces" / f"{datetime.now(UTC).date()}.jsonl"
    trace_text = trace_path.read_text(encoding="utf-8")
    assert "retrieval_requested" in trace_text
    assert "retrieval_context_built" in trace_text
    assert "trace context body must not be logged" not in trace_text
