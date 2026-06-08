import json

from typer.testing import CliRunner

from agentos.cli.app import app
from agentos.mcp.adapter import AgentOSMCPAdapter
from agentos.mcp.server import handle_jsonrpc_message
from agentos.services.container import create_service_container

runner = CliRunner()


def test_mcp_tool_schemas_expose_allowed_tools_only(tmp_path):
    adapter = AgentOSMCPAdapter(create_service_container(tmp_path))

    names = {tool["name"] for tool in adapter.list_tools()}

    assert names == {
        "memory_add",
        "memory_search",
        "memory_get",
        "sdd_new",
        "sdd_status",
        "skills_list",
        "policies_check",
    }
    assert "memory_delete" not in names
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


def test_mcp_serve_cli_exits_on_eof_without_hanging(tmp_path):
    result = runner.invoke(app, ["mcp", "serve", "--root", str(tmp_path)], input="")

    assert result.exit_code == 0
    assert "AgentOS MCP server listening on stdio" in result.stderr
