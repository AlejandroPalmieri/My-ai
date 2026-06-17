import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from agentos.agents.planner import parse_tool_protocol
from agentos.agents.tool_loop import AgentToolLoop
from agentos.brain.store import StrategicBrainStore
from agentos.cli.app import app
from agentos.memory.store import MemoryStore
from agentos.tools.builtin_tools import create_builtin_tool_registry
from agentos.tools.executor import ToolExecutor
from agentos.tools.registry import ToolRegistry
from agentos.tools.schemas import ToolCall, ToolDefinition, ToolExecutionContext

runner = CliRunner()


def test_tool_registry_lists_builtin_tools():
    registry = create_builtin_tool_registry()
    names = {tool.name for tool in registry.list_tools()}

    assert names == {
        "memory_search",
        "memory_add",
        "brain_search",
        "sdd_new",
        "sdd_status",
        "skills_list",
        "policies_check",
        "usage_summary",
    }


def test_unknown_tool_blocked(tmp_path):
    result = ToolExecutor(tmp_path, create_builtin_tool_registry()).execute(
        ToolCall(name="shell", arguments={"command": "echo unsafe"})
    )

    assert result.status == "blocked"
    assert "Unknown tool" in (result.error or "")


def test_policy_check_tool_works(tmp_path):
    result = ToolExecutor(tmp_path, create_builtin_tool_registry()).execute(
        ToolCall(name="policies_check", arguments={"command": "rm -rf project"})
    )

    assert result.status == "ok"
    assert result.output["severity"] == "block"


def test_memory_search_tool_works(tmp_path):
    MemoryStore(tmp_path).add_memory(
        "default",
        "Architecture note",
        "decision",
        "Use allowlisted tools only.",
        [],
    )

    result = ToolExecutor(tmp_path, create_builtin_tool_registry()).execute(
        ToolCall(name="memory_search", arguments={"query": "allowlisted"})
    )

    assert result.status == "ok"
    assert result.output["memories"][0]["title"] == "Architecture note"


def test_brain_search_tool_works(tmp_path):
    note = tmp_path / "strategy.md"
    note.write_text("# Strategy\n\nTool calling must stay allowlisted.", encoding="utf-8")
    StrategicBrainStore(tmp_path).ingest_document(note)

    result = ToolExecutor(tmp_path, create_builtin_tool_registry()).execute(
        ToolCall(name="brain_search", arguments={"query": "allowlisted"})
    )

    assert result.status == "ok"
    assert result.output["documents"][0]["title"] == "Strategy"


def test_local_stub_agent_can_call_fake_tool(tmp_path):
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="fake_tool",
            description="Fake safe tool for tests.",
            input_schema={"type": "object", "properties": {}, "required": []},
            output_schema={"type": "object", "properties": {}},
        ),
        lambda _root, args: {"called": True, "query": args.get("query", "")},
    )

    result = AgentToolLoop(tmp_path, registry=registry).run(
        name="Tester",
        role="testing",
        task="use fake tool",
        max_steps=3,
    )

    assert result.status == "completed"
    assert result.tool_results[0].tool_name == "fake_tool"
    assert result.tool_results[0].output["called"] is True


def test_max_steps_enforced(tmp_path):
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="fake_tool",
            description="Fake safe tool for tests.",
            input_schema={"type": "object", "properties": {}, "required": []},
            output_schema={"type": "object", "properties": {}},
        ),
        lambda _root, _args: {"called": True},
    )

    result = AgentToolLoop(tmp_path, registry=registry).run(
        name="Tester",
        role="testing",
        task="use fake tool repeatedly",
        max_steps=1,
    )

    assert result.final_answer == "Stopped after max steps."
    assert len(result.tool_results) == 1


def test_requires_approval_behavior(tmp_path):
    executor = ToolExecutor(tmp_path, create_builtin_tool_registry())
    call = ToolCall(
        name="memory_add",
        arguments={"title": "Approved", "content": "Only with approval."},
    )

    blocked = executor.execute(call)
    approved = executor.execute(call, ToolExecutionContext(approvals={"memory_add"}))

    assert blocked.status == "blocked"
    assert blocked.requires_approval is True
    assert approved.status == "ok"


def test_max_calls_per_run_enforced_with_shared_context(tmp_path):
    registry = ToolRegistry()
    calls = {"count": 0}

    def handler(_root, _args):
        calls["count"] += 1
        return {"called": calls["count"]}

    registry.register(
        ToolDefinition(
            name="limited_tool",
            description="Limited safe tool for tests.",
            input_schema={"type": "object", "properties": {}, "required": []},
            output_schema={"type": "object", "properties": {}},
            max_calls_per_run=1,
        ),
        handler,
    )
    executor = ToolExecutor(tmp_path, registry)
    context = ToolExecutionContext()
    call = ToolCall(name="limited_tool", arguments={})

    first = executor.execute(call, context)
    second = executor.execute(call, context)

    assert first.status == "ok"
    assert second.status == "blocked"
    assert "max_calls_per_run" in (second.error or "")
    assert calls["count"] == 1
    assert context.call_counts == {"limited_tool": 1}


def test_tool_traces_created(tmp_path):
    ToolExecutor(tmp_path, create_builtin_tool_registry()).execute(
        ToolCall(name="usage_summary", arguments={})
    )
    trace_path = tmp_path / ".agentos" / "traces" / f"{datetime.now(UTC).date()}.jsonl"
    trace_text = trace_path.read_text(encoding="utf-8")

    assert "tool_call_requested" in trace_text
    assert "tool_call_allowed" in trace_text
    assert "tool_call_completed" in trace_text


def test_usage_summary_tool_does_not_redact_safe_token_keys(tmp_path):
    result = ToolExecutor(tmp_path, create_builtin_tool_registry()).execute(
        ToolCall(name="usage_summary", arguments={})
    )

    assert result.status == "ok"
    assert result.output["total_tokens"] == 0


def test_no_shell_execution_tool_exists():
    names = {tool.name for tool in create_builtin_tool_registry().list_tools()}

    assert "shell" not in names
    assert "command_exec" not in names
    assert "file_read" not in names
    assert "file_write" not in names


def test_parse_tool_protocol_valid_tool_call_json():
    message = parse_tool_protocol(
        'model text {"tool_calls":[{"name":"memory_search","arguments":{"query":"architecture"}}],'
        '"final_answer":null} trailing text'
    )

    assert len(message.tool_calls) == 1
    assert message.tool_calls[0].name == "memory_search"
    assert message.tool_calls[0].arguments == {"query": "architecture"}
    assert message.final_answer is None


def test_parse_tool_protocol_valid_final_answer_json():
    message = parse_tool_protocol('{"tool_calls":[],"final_answer":"No tools needed."}')

    assert message.tool_calls == []
    assert message.final_answer == "No tools needed."


def test_parse_tool_protocol_malformed_json_falls_back_to_final_answer():
    raw = 'not json {"tool_calls":['

    message = parse_tool_protocol(raw)

    assert message.tool_calls == []
    assert message.final_answer == raw


def test_parse_tool_protocol_invalid_schema_raises_validation_error():
    with pytest.raises(ValidationError):
        parse_tool_protocol('{"tool_calls":"memory_search","final_answer":null}')


def test_tools_cli_list_show_and_test(tmp_path):
    listed = runner.invoke(app, ["tools", "list", "--root", str(tmp_path)])
    shown = runner.invoke(app, ["tools", "show", "memory_search", "--root", str(tmp_path)])
    tested = runner.invoke(
        app,
        [
            "tools",
            "test",
            "policies_check",
            "--json-input",
            json.dumps({"command": "pytest"}),
            "--root",
            str(tmp_path),
        ],
    )

    assert listed.exit_code == 0
    assert "memory_search" in listed.output
    assert shown.exit_code == 0
    assert '"name": "memory_search"' in shown.output
    assert tested.exit_code == 0
    assert '"severity": "allow"' in tested.output


def test_agents_run_with_tools_cli(tmp_path):
    result = runner.invoke(
        app,
        [
            "agents",
            "run",
            "--task",
            "search memory for architecture",
            "--tools",
            "--max-steps",
            "5",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "tool=memory_search status=ok" in result.output
