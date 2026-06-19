from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import IO, Any

from agentos import __version__
from agentos.evals.reports import safe_report_text
from agentos.mcp.adapter import AgentOSMCPAdapter
from agentos.mcp.tools import ALLOWED_TOOL_NAMES, BLOCKED_TOOL_NAMES
from agentos.services.container import create_service_container

JSONRPC_VERSION = "2.0"
LOCAL_PATH_PATTERN = re.compile(r"(?<![\w.-])(?:/[A-Za-z0-9._~+\-]+)+")


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
    print("AgentOS MCP server stopped after EOF", file=sys.stderr)


def handle_jsonrpc_line(line: str, adapter: AgentOSMCPAdapter) -> dict[str, Any] | None:
    try:
        message = json.loads(line)
    except json.JSONDecodeError as error:
        return _error_response(None, -32700, f"Parse error: {error.msg}")
    return handle_jsonrpc_message(message, adapter)


def handle_jsonrpc_message(
    message: object,
    adapter: AgentOSMCPAdapter,
) -> dict[str, Any] | None:
    if not isinstance(message, dict):
        return _error_response(None, -32600, "Invalid Request: message must be an object.")
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
            if "params" in message and not isinstance(message.get("params"), dict):
                return _error_response(request_id, -32602, "Tool call params must be an object.")
            params = message.get("params") if isinstance(message.get("params"), dict) else {}
            return _result_response(request_id, _call_tool_result(params, adapter))
        if method == "ping":
            return _result_response(request_id, {})
        return _error_response(request_id, -32601, "Method not found.")
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
    try:
        payload = adapter.call_tool(name, arguments)
    except KeyError as error:
        return _tool_error_result("unknown_tool", _clean_error_message(error))
    except (PermissionError, FileNotFoundError, TypeError, ValueError) as error:
        return _tool_error_result("tool_error", _clean_error_message(error))
    except Exception:
        return _tool_error_result("internal_error", "Internal tool error.")
    return {
        "content": [{"type": "text", "text": json.dumps(payload, sort_keys=True)}],
        "isError": False,
    }


def mcp_status(root: Path) -> dict[str, Any]:
    adapter = AgentOSMCPAdapter(create_service_container(root))
    return {
        "transport": "stdio",
        "local_only": True,
        "network_server": False,
        "implementation": "custom-json-rpc-stdio",
        "sdk": {
            "candidate": "official Model Context Protocol Python SDK (mcp)",
            "adoption": "deferred",
            "dependency_added": False,
        },
        "startup": "stderr status message; JSON-RPC responses on stdout",
        "shutdown": "clean EOF shutdown",
        "tool_count": len(adapter.list_tools()),
        "tools": list(ALLOWED_TOOL_NAMES),
        "blocked_tools": list(BLOCKED_TOOL_NAMES),
    }


def _tool_error_result(error_type: str, message: str) -> dict[str, Any]:
    payload = {"error": {"type": error_type, "message": message}}
    return {
        "content": [{"type": "text", "text": json.dumps(payload, sort_keys=True)}],
        "isError": True,
    }


def _clean_error_message(error: Exception) -> str:
    message = str(error)
    if isinstance(error, KeyError):
        cleaned = message.strip("'")
        if cleaned.startswith("Unknown MCP tool:"):
            return "Unknown MCP tool."
        return "Requested MCP resource was not found."
    if isinstance(error, FileNotFoundError):
        return "Requested MCP resource was not found."
    if isinstance(error, PermissionError):
        return "MCP tool request was denied by policy."
    if isinstance(error, TypeError):
        return "Invalid MCP tool arguments."
    return _sanitize_error_text(message)


def _sanitize_error_text(message: str) -> str:
    redacted = safe_report_text(message)
    redacted = LOCAL_PATH_PATTERN.sub("[REDACTED_PATH]", redacted).strip()
    return redacted or "Invalid MCP tool request."


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
