from __future__ import annotations

from pathlib import Path
from typing import Any

from agentos.brain.store import StrategicBrainStore
from agentos.memory.store import MemoryStore
from agentos.policies.checker import PolicyChecker, create_default_policies
from agentos.sdd.generator import create_change, get_change_status, list_changes
from agentos.skills.registry import scan_skills
from agentos.tools.registry import ToolRegistry
from agentos.tools.schemas import ToolDefinition, ToolRiskLevel
from agentos.usage.store import UsageStore


def create_builtin_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for definition, handler in _BUILTINS:
        registry.register(definition, handler)
    return registry


def _schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required or []}


def _memory_search(root: Path, args: dict[str, Any]) -> dict[str, Any]:
    query = str(args.get("query", "")).strip()
    project = _optional_str(args.get("project"))
    limit = _limit(args.get("limit"), default=5)
    memories = MemoryStore(root).search(query, project=project, limit=limit) if query else []
    return {
        "memories": [
            {
                "id": memory.id,
                "title": memory.title,
                "kind": memory.kind,
                "project": memory.project,
                "content": _excerpt(memory.content),
            }
            for memory in memories
        ]
    }


def _memory_add(root: Path, args: dict[str, Any]) -> dict[str, Any]:
    title = str(args.get("title", "")).strip()
    content = str(args.get("content", "")).strip()
    project = str(args.get("project") or "default").strip() or "default"
    kind = str(args.get("kind") or "agent-note").strip() or "agent-note"
    memory = MemoryStore(root).add_memory(
        project=project,
        title=title,
        kind=kind,
        content=content,
        tags=["agent-tool"],
        source="agent-tool",
    )
    return {"memory_id": memory.id, "title": memory.title, "project": memory.project}


def _brain_search(root: Path, args: dict[str, Any]) -> dict[str, Any]:
    query = str(args.get("query", "")).strip()
    limit = _limit(args.get("limit"), default=5)
    results = StrategicBrainStore(root).search(query, limit=limit) if query else []
    return {
        "documents": [
            {
                "document_id": item.document_id,
                "title": item.title,
                "path": item.path,
                "chunk_index": item.chunk_index,
                "chunk": _excerpt(item.chunk),
            }
            for item in results
        ]
    }


def _sdd_new(root: Path, args: dict[str, Any]) -> dict[str, Any]:
    change_name = str(args.get("change_name", "")).strip()
    change = create_change(root, change_name)
    return {"change_name": change.name, "phase": change.phase, "path": str(change.path)}


def _sdd_status(root: Path, args: dict[str, Any]) -> dict[str, Any]:
    change_name = _optional_str(args.get("change_name"))
    if change_name:
        change = get_change_status(root, change_name)
        return {"change_name": change.name, "phase": change.phase, "archived": change.archived}
    return {
        "changes": [
            {"change_name": change.name, "phase": change.phase, "archived": change.archived}
            for change in list_changes(root)
        ]
    }


def _skills_list(root: Path, args: dict[str, Any]) -> dict[str, Any]:
    registry = scan_skills(root)
    return {
        "skills": [
            {
                "name": skill.name,
                "description": skill.description,
                "path": skill.path,
                "valid": skill.valid,
            }
            for skill in registry.skills
        ],
        "warnings": registry.warnings,
    }


def _policies_check(root: Path, args: dict[str, Any]) -> dict[str, Any]:
    create_default_policies(root)
    checker = PolicyChecker.from_directory(root / "policies")
    path = _optional_str(args.get("path"))
    command = _optional_str(args.get("command"))
    if path:
        result = checker.check_path(path)
    elif command:
        result = checker.check_command(command)
    else:
        raise ValueError("policies_check requires `path` or `command`.")
    return result.model_dump(mode="json")


def _usage_summary(root: Path, args: dict[str, Any]) -> dict[str, Any]:
    summary = UsageStore(root).summary()
    return summary.model_dump(mode="json")


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _limit(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(0, min(parsed, 20))


def _excerpt(value: str, limit: int = 240) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


_BUILTINS = [
    (
        ToolDefinition(
            name="memory_search",
            description="Search local technical memory excerpts.",
            input_schema=_schema(
                {
                    "query": {"type": "string"},
                    "project": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 0, "maximum": 20},
                },
                ["query"],
            ),
            output_schema=_schema({"memories": {"type": "array"}}),
        ),
        _memory_search,
    ),
    (
        ToolDefinition(
            name="memory_add",
            description="Add a short local technical memory after approval.",
            input_schema=_schema(
                {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "project": {"type": "string"},
                    "kind": {"type": "string"},
                },
                ["title", "content"],
            ),
            output_schema=_schema({"memory_id": {"type": "string"}}),
            risk_level=ToolRiskLevel.REVIEW,
            requires_approval=True,
        ),
        _memory_add,
    ),
    (
        ToolDefinition(
            name="brain_search",
            description="Search the local Strategic Brain index.",
            input_schema=_schema(
                {"query": {"type": "string"}, "limit": {"type": "integer"}},
                ["query"],
            ),
            output_schema=_schema({"documents": {"type": "array"}}),
        ),
        _brain_search,
    ),
    (
        ToolDefinition(
            name="sdd_new",
            description="Create a new SDD/OpenSpec change artifact.",
            input_schema=_schema({"change_name": {"type": "string"}}, ["change_name"]),
            output_schema=_schema({"change_name": {"type": "string"}}),
            risk_level=ToolRiskLevel.REVIEW,
            requires_approval=True,
            max_calls_per_run=1,
        ),
        _sdd_new,
    ),
    (
        ToolDefinition(
            name="sdd_status",
            description="Show status for one SDD change or list all changes.",
            input_schema=_schema({"change_name": {"type": "string"}}),
            output_schema=_schema({"changes": {"type": "array"}}),
        ),
        _sdd_status,
    ),
    (
        ToolDefinition(
            name="skills_list",
            description="List local AgentOS skills metadata.",
            input_schema=_schema({}),
            output_schema=_schema({"skills": {"type": "array"}}),
        ),
        _skills_list,
    ),
    (
        ToolDefinition(
            name="policies_check",
            description="Check one path or command string with local policy rules.",
            input_schema=_schema({"path": {"type": "string"}, "command": {"type": "string"}}),
            output_schema=_schema({"severity": {"type": "string"}}),
        ),
        _policies_check,
    ),
    (
        ToolDefinition(
            name="usage_summary",
            description="Summarize local model usage accounting.",
            input_schema=_schema({}),
            output_schema=_schema({"total_tokens": {"type": "integer"}}),
        ),
        _usage_summary,
    ),
]
