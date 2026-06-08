from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import IO, Any

from agentos import __version__
from agentos.mcp.adapter import AgentOSMCPAdapter
from agentos.services.container import create_service_container

JSONRPC_VERSION = "2.0"


def serve_stdio(root: Path, stdin: IO[str] | None = None, stdout: IO[str] | None = None) -> None:
    input_stream = stdin or sys.stdin
    output_stream = stdout or sys.stdout
    adapter = AgentOSMCPAdapter(create_service_container(root))
    print("AgentOS MCP server listening on stdio", file=sys.stderr)
    for line in input_stream:
        if not line.strip():
            continue
        response = handle_jsonrpc_line(line, adapter)
        if response is None:
            continue
        output_stream.write(json.dumps(response, sort_keys=True) + "\n")
        output_stream.flush()


def handle_jsonrpc_line(line: str, adapter: AgentOSMCPAdapter) -> dict[str, Any] | None:
    try:
        message = json.loads(line)
    except json.JSONDecodeError as error:
        return _error_response(None, -32700, f"Parse error: {error.msg}")
    return handle_jsonrpc_message(message, adapter)


def handle_jsonrpc_message(
    message: dict[str, Any],
    adapter: AgentOSMCPAdapter,
) -> dict[str, Any] | None:
    request_id = message.get("id")
    method = message.get("method")
    if request_id is None and method:
        return None
    try:
        if method == "initialize":
            return _result_response(request_id, _initialize_result())
        if method == "tools/list":
            return _result_response(request_id, {"tools": adapter.list_tools()})
        if method == "tools/call":
            params = message.get("params") if isinstance(message.get("params"), dict) else {}
            return _result_response(request_id, _call_tool_result(params, adapter))
        if method == "ping":
            return _result_response(request_id, {})
        return _error_response(request_id, -32601, f"Method not found: {method}")
    except (KeyError, TypeError, ValueError) as error:
        return _error_response(request_id, -32602, str(error))
    except Exception as error:
        return _error_response(request_id, -32603, str(error))


def _initialize_result() -> dict[str, Any]:
    return {
        "protocolVersion": "2024-11-05",
        "serverInfo": {"name": "agentos", "version": __version__},
        "capabilities": {"tools": {}},
    }


def _call_tool_result(params: dict[str, Any], adapter: AgentOSMCPAdapter) -> dict[str, Any]:
    name = params.get("name")
    if not isinstance(name, str):
        raise ValueError("Missing tool name.")
    arguments = params.get("arguments")
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be an object.")
    payload = adapter.call_tool(name, arguments)
    return {
        "content": [{"type": "text", "text": json.dumps(payload, sort_keys=True)}],
        "isError": False,
    }


def _result_response(request_id: object, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "result": result}


def _error_response(
    request_id: object,
    code: int,
    message: str,
) -> dict[str, Any]:
    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": request_id,
        "error": {"code": code, "message": message},
    }
