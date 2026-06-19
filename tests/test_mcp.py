import json

from typer.testing import CliRunner

from agentos.agents.registry import AgentRuntimeRegistry
from agentos.brain.store import StrategicBrainStore
from agentos.cli.app import app
from agentos.mcp.adapter import AgentOSMCPAdapter
from agentos.mcp.server import handle_jsonrpc_message
from agentos.mcp.tools import ALLOWED_TOOL_NAMES, BLOCKED_TOOL_NAMES
from agentos.models.config import create_default_model_config, set_active_model_profile
from agentos.services.container import create_service_container
from agentos.usage.store import UsageStore

runner = CliRunner()

EXPECTED_ALLOWED_TOOL_NAMES = {
    "memory_add",
    "memory_search",
    "memory_get",
    "brain_search",
    "sdd_new",
    "sdd_status",
    "skills_list",
    "policies_check",
    "models_status",
    "usage_summary",
    "agents_status",
}

EXPECTED_BLOCKED_TOOL_NAMES = {
    "memory_delete",
    "backup_restore",
    "shell",
    "shell_execute",
    "command_run",
    "file_read",
    "file_write",
    "update",
    "self_update",
    "uninstall",
}


def test_mcp_tool_schemas_expose_allowed_tools_only(tmp_path):
    adapter = AgentOSMCPAdapter(create_service_container(tmp_path))

    names = {tool["name"] for tool in adapter.list_tools()}

    assert names == EXPECTED_ALLOWED_TOOL_NAMES
    assert set(ALLOWED_TOOL_NAMES) == EXPECTED_ALLOWED_TOOL_NAMES
    assert set(BLOCKED_TOOL_NAMES) == EXPECTED_BLOCKED_TOOL_NAMES
    assert names.isdisjoint(EXPECTED_BLOCKED_TOOL_NAMES)
    assert adapter.tool_by_name("memory_add")["inputSchema"]["type"] == "object"


def test_mcp_adapter_calls_memory_and_policy_tools(tmp_path):
    adapter = AgentOSMCPAdapter(create_service_container(tmp_path))

    added = adapter.call_tool(
        "memory_add",
        {
            "project": "demo",
            "title": "MCP note",
            "kind": "note",
            "content": "Local MCP searchable content",
            "tags": ["mcp"],
        },
    )
    found = adapter.call_tool("memory_search", {"query": "searchable", "project": "demo"})
    policy = adapter.call_tool("policies_check", {"path": ".env"})

    assert added["title"] == "MCP note"
    assert found["memories"][0]["title"] == "MCP note"
    assert policy["results"][0]["severity"] == "block"
    assert policy["results"][0]["matched_rule"] == ".env"


def test_mcp_adapter_calls_selected_status_and_search_tools(tmp_path, monkeypatch):
    note = tmp_path / "strategy.md"
    note.write_text("# Strategy\n\nMCP brain search returns bounded excerpts.", encoding="utf-8")
    StrategicBrainStore(tmp_path).ingest_document(note)
    UsageStore(tmp_path).record_event(
        session_id="session-1",
        project="default",
        profile="openai-gpt-5-5",
        provider="openai",
        model="gpt-5.5",
        effort="medium",
        agent_id="agent-1",
        command="chat.once",
        input_tokens=8,
        output_tokens=4,
        estimated_cost_usd=0.01,
        context_used_percent=2.0,
    )
    agent = AgentRuntimeRegistry(tmp_path).start_agent(
        name="Planner",
        role="planning",
        current_task="Plan MCP status coverage",
        model_profile="local-stub",
    )
    create_default_model_config(tmp_path)
    set_active_model_profile(tmp_path, "openai-gpt-5-5")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret-value")
    adapter = AgentOSMCPAdapter(create_service_container(tmp_path))

    brain = adapter.call_tool("brain_search", {"query": "bounded", "limit": 5})
    models = adapter.call_tool("models_status")
    usage = adapter.call_tool("usage_summary")
    agents = adapter.call_tool("agents_status")
    policy = adapter.call_tool("policies_check", {"command": "rm -rf project"})

    assert brain["documents"][0]["title"] == "Strategy"
    assert "content" not in brain["documents"][0]
    assert models["api_key_env"] == "OPENAI_API_KEY"
    assert "sk-secret-value" not in json.dumps(models)
    assert usage["summary"]["total_tokens"] == 12
    assert agents["active_count"] == 1
    assert agents["agents"][0]["id"] == agent.id
    assert policy["results"][0]["severity"] == "block"


def test_mcp_policy_reasons_do_not_echo_sensitive_inputs(tmp_path):
    adapter = AgentOSMCPAdapter(create_service_container(tmp_path))
    command = "rm -rf project --token=sk-secret-value"
    path = "/home/example/project/.env?api_key=secret-value"

    payload = adapter.call_tool("policies_check", {"command": command, "path": path})

    serialized = json.dumps(payload)
    assert command not in serialized
    assert path not in serialized
    assert "sk-secret-value" not in serialized
    assert "secret-value" not in serialized
    assert {result["reason"] for result in payload["results"]} == {
        "Blocked sensitive path.",
        "Blocked command.",
    }


def test_mcp_memory_get_tool(tmp_path):
    adapter = AgentOSMCPAdapter(create_service_container(tmp_path))
    added = adapter.call_tool(
        "memory_add",
        {"project": "demo", "title": "Lookup", "content": "Retrieve by id."},
    )

    loaded = adapter.call_tool("memory_get", {"memory_id": added["id"]})

    assert loaded["id"] == added["id"]
    assert loaded["title"] == "Lookup"


def test_mcp_jsonrpc_tools_list_and_call(tmp_path):
    adapter = AgentOSMCPAdapter(create_service_container(tmp_path))

    list_response = handle_jsonrpc_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        },
        adapter,
    )
    call_response = handle_jsonrpc_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "policies_check", "arguments": {"command": "git status"}},
        },
        adapter,
    )

    assert list_response["result"]["tools"][0]["name"] == "memory_add"
    content = call_response["result"]["content"][0]
    assert content["type"] == "text"
    assert json.loads(content["text"])["results"][0]["severity"] == "allow"


def test_mcp_jsonrpc_rejects_non_object_messages(tmp_path):
    adapter = AgentOSMCPAdapter(create_service_container(tmp_path))

    list_response = handle_jsonrpc_message([], adapter)
    string_response = handle_jsonrpc_message("x", adapter)

    assert list_response["error"]["code"] == -32600
    assert string_response["error"]["code"] == -32600


def test_mcp_jsonrpc_blocked_tools_return_normalized_tool_errors(tmp_path):
    adapter = AgentOSMCPAdapter(create_service_container(tmp_path))

    for blocked_name in BLOCKED_TOOL_NAMES:
        response = handle_jsonrpc_message(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": blocked_name, "arguments": {"command": "echo unsafe"}},
            },
            adapter,
        )

        assert "error" not in response
        assert response["result"]["isError"] is True
        payload = json.loads(response["result"]["content"][0]["text"])
        assert payload["error"] == {
            "type": "unknown_tool",
            "message": "Unknown MCP tool.",
        }


def test_mcp_jsonrpc_tool_errors_do_not_echo_local_paths_or_secrets(tmp_path):
    class LeakyAdapter:
        def call_tool(self, _name, _arguments):
            raise FileNotFoundError("/home/example/project/.env token=sk-secret-value")

    response = handle_jsonrpc_message(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "memory_get", "arguments": {"memory_id": "missing"}},
        },
        LeakyAdapter(),
    )

    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["error"] == {
        "type": "tool_error",
        "message": "Requested MCP resource was not found.",
    }
    assert "/home/example/project" not in response["result"]["content"][0]["text"]
    assert "sk-secret-value" not in response["result"]["content"][0]["text"]


def test_mcp_serve_cli_exits_on_eof_without_hanging(tmp_path):
    result = runner.invoke(app, ["mcp", "serve", "--root", str(tmp_path)], input="")

    assert result.exit_code == 0
    assert "AgentOS MCP server listening on stdio" in result.stderr
    assert "AgentOS MCP server stopped after EOF" in result.stderr


def test_mcp_tools_and_status_cli(tmp_path):
    tools_result = runner.invoke(app, ["mcp", "tools", "--root", str(tmp_path)])
    status_result = runner.invoke(app, ["mcp", "status", "--root", str(tmp_path)])

    assert tools_result.exit_code == 0
    assert "memory_add" in tools_result.output
    assert "agents_status" in tools_result.output
    assert "memory_delete" not in tools_result.output
    assert status_result.exit_code == 0
    assert "custom-json-rpc-stdio" in status_result.output
    assert "sdk_adoption=deferred" in status_result.output
    assert "dependency_added=False" in status_result.output
