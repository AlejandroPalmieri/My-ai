from __future__ import annotations

from typing import Any

from agentos.mcp.tools import tool_definition, tool_definitions
from agentos.services.container import ServiceContainer


class AgentOSMCPAdapter:
    def __init__(self, services: ServiceContainer) -> None:
        self.services = services

    def list_tools(self) -> list[dict[str, object]]:
        return tool_definitions()

    def tool_by_name(self, name: str) -> dict[str, object]:
        return tool_definition(name)

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        args = arguments or {}
        if name == "memory_add":
            return self._memory_add(args)
        if name == "memory_search":
            return self._memory_search(args)
        if name == "memory_get":
            return self._memory_get(args)
        if name == "sdd_new":
            return self._sdd_new(args)
        if name == "sdd_status":
            return self._sdd_status(args)
        if name == "skills_list":
            return self._skills_list()
        if name == "policies_check":
            return self._policies_check(args)
        raise KeyError(f"Unknown MCP tool: {name}")

    def _memory_add(self, args: dict[str, Any]) -> dict[str, Any]:
        project = self.services.profiles.resolve_memory_project(_optional_string(args, "project"))
        memory = self.services.memory.add_memory(
            project=project,
            title=_required_string(args, "title"),
            kind=str(args.get("kind") or "note"),
            content=_required_string(args, "content"),
            tags=_string_list(args.get("tags")),
            source=_optional_string(args, "source"),
            confidence=float(args.get("confidence", 1.0)),
        )
        return memory.model_dump(mode="json")

    def _memory_search(self, args: dict[str, Any]) -> dict[str, Any]:
        results = self.services.memory.search_memories(
            _required_string(args, "query"),
            project=_optional_string(args, "project"),
            limit=int(args.get("limit", 20)),
        )
        return {"memories": [memory.model_dump(mode="json") for memory in results]}

    def _memory_get(self, args: dict[str, Any]) -> dict[str, Any]:
        memory = self.services.memory.get_memory(_required_string(args, "memory_id"))
        if memory is None:
            raise KeyError(f"Memory not found: {_required_string(args, 'memory_id')}")
        return memory.model_dump(mode="json")

    def _sdd_new(self, args: dict[str, Any]) -> dict[str, Any]:
        change = self.services.sdd.create_change(_required_string(args, "change_name"))
        return _change_payload(change)

    def _sdd_status(self, args: dict[str, Any]) -> dict[str, Any]:
        change = self.services.sdd.get_status(_required_string(args, "change_name"))
        return _change_payload(change)

    def _skills_list(self) -> dict[str, Any]:
        registry = self.services.skills.list()
        return {
            "skills": [skill.model_dump(mode="json") for skill in registry.skills],
            "warnings": registry.warnings,
        }

    def _policies_check(self, args: dict[str, Any]) -> dict[str, Any]:
        results = []
        path = _optional_string(args, "path")
        command = _optional_string(args, "command")
        if path is not None:
            results.append(self.services.policies.check_path(path))
        if command is not None:
            results.append(self.services.policies.check_command(command))
        if not results:
            raise ValueError("Provide path or command.")
        return {"results": [_policy_payload(result) for result in results]}


def _required_string(args: dict[str, Any], key: str) -> str:
    value = args.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing required string argument: {key}")
    return value


def _optional_string(args: dict[str, Any], key: str) -> str | None:
    value = args.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"Expected string argument: {key}")
    return value


def _string_list(value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("Expected tags to be a list of strings.")
    return [str(item) for item in value]


def _change_payload(change) -> dict[str, Any]:
    return {
        "name": change.name,
        "phase": change.phase,
        "archived": change.archived,
        "path": str(change.path),
        "files": [str(path) for path in change.files],
    }


def _policy_payload(result) -> dict[str, Any]:
    return {
        "severity": result.severity.value,
        "allowed": result.allowed,
        "reason": result.reason,
        "matched_rule": result.matched_rule,
        "rule_type": result.rule_type,
    }
