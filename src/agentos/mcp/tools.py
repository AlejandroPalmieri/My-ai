from __future__ import annotations

from copy import deepcopy


def tool_definitions() -> list[dict[str, object]]:
    return deepcopy(_TOOLS)


def tool_definition(name: str) -> dict[str, object]:
    for tool in _TOOLS:
        if tool["name"] == name:
            return deepcopy(tool)
    raise KeyError(f"Unknown MCP tool: {name}")


def _object_schema(
    properties: dict[str, dict[str, object]],
    required: list[str] | None = None,
) -> dict[str, object]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


ALLOWED_TOOL_NAMES = (
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
)

BLOCKED_TOOL_NAMES = (
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
)


_TOOLS: list[dict[str, object]] = [
    {
        "name": "memory_add",
        "description": "Add a local AgentOS technical memory.",
        "inputSchema": _object_schema(
            {
                "project": {"type": "string", "description": "Memory project."},
                "title": {"type": "string", "description": "Memory title."},
                "kind": {"type": "string", "description": "Memory kind.", "default": "note"},
                "content": {"type": "string", "description": "Memory content."},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional memory tags.",
                    "default": [],
                },
                "source": {"type": "string", "description": "Optional source."},
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Confidence score.",
                    "default": 1.0,
                },
            },
            ["title", "content"],
        ),
    },
    {
        "name": "memory_search",
        "description": "Search local AgentOS technical memories.",
        "inputSchema": _object_schema(
            {
                "query": {"type": "string", "description": "Search query."},
                "project": {"type": "string", "description": "Optional project filter."},
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "description": "Maximum results.",
                    "default": 20,
                },
            },
            ["query"],
        ),
    },
    {
        "name": "memory_get",
        "description": "Get a local AgentOS technical memory by ID.",
        "inputSchema": _object_schema(
            {"memory_id": {"type": "string", "description": "Memory ID."}},
            ["memory_id"],
        ),
    },
    {
        "name": "brain_search",
        "description": "Search indexed Strategic Brain documents and return bounded excerpts.",
        "inputSchema": _object_schema(
            {
                "query": {"type": "string", "description": "Search query."},
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Maximum excerpt results.",
                    "default": 5,
                },
            },
            ["query"],
        ),
    },
    {
        "name": "sdd_new",
        "description": "Create a local SDD/OpenSpec change.",
        "inputSchema": _object_schema(
            {"change_name": {"type": "string", "description": "Lowercase change slug."}},
            ["change_name"],
        ),
    },
    {
        "name": "sdd_status",
        "description": "Show local SDD/OpenSpec change status.",
        "inputSchema": _object_schema(
            {"change_name": {"type": "string", "description": "Change slug."}},
            ["change_name"],
        ),
    },
    {
        "name": "skills_list",
        "description": "List local AgentOS skills without loading full skill content.",
        "inputSchema": _object_schema({}),
    },
    {
        "name": "policies_check",
        "description": (
            "Check a path or command against local AgentOS policies without executing it."
        ),
        "inputSchema": _object_schema(
            {
                "path": {"type": "string", "description": "Optional path to check."},
                "command": {
                    "type": "string",
                    "description": "Optional command text to check. It is not executed.",
                },
            },
        ),
    },
    {
        "name": "models_status",
        "description": "Show local model provider readiness without exposing secret values.",
        "inputSchema": _object_schema({}),
    },
    {
        "name": "usage_summary",
        "description": "Show aggregate local token and estimated cost usage metadata.",
        "inputSchema": _object_schema({}),
    },
    {
        "name": "agents_status",
        "description": "Show local agent runtime status metadata.",
        "inputSchema": _object_schema({}),
    },
]


assert tuple(tool["name"] for tool in _TOOLS) == ALLOWED_TOOL_NAMES
