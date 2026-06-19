from __future__ import annotations

from typing import Any

from agentos.agents.registry import ACTIVE_STATUSES, AgentRuntimeRegistry
from agentos.evals.reports import safe_report_text
from agentos.mcp.tools import tool_definition, tool_definitions
from agentos.models.config import inspect_model_status
from agentos.retrieval.brain_retriever import retrieve_brain
from agentos.services.container import ServiceContainer
from agentos.usage.store import UsageStore


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
        if name == "brain_search":
            return self._brain_search(args)
        if name == "sdd_new":
            return self._sdd_new(args)
        if name == "sdd_status":
            return self._sdd_status(args)
        if name == "skills_list":
            return self._skills_list()
        if name == "policies_check":
            return self._policies_check(args)
        if name == "models_status":
            return self._models_status()
        if name == "usage_summary":
            return self._usage_summary()
        if name == "agents_status":
            return self._agents_status()
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
        limit = _bounded_limit(args.get("limit"), default=20, maximum=50)
        results = self.services.memory.search_memories(
            _required_string(args, "query"),
            project=_optional_string(args, "project"),
            limit=limit,
        )
        return {"memories": [memory.model_dump(mode="json") for memory in results]}

    def _memory_get(self, args: dict[str, Any]) -> dict[str, Any]:
        memory = self.services.memory.get_memory(_required_string(args, "memory_id"))
        if memory is None:
            raise KeyError(f"Memory not found: {_required_string(args, 'memory_id')}")
        return memory.model_dump(mode="json")

    def _brain_search(self, args: dict[str, Any]) -> dict[str, Any]:
        limit = _bounded_limit(args.get("limit"), default=5, maximum=10)
        results = retrieve_brain(
            self.services.root,
            _required_string(args, "query"),
            limit=limit,
        )
        return {"documents": [item.model_dump(mode="json") for item in results]}

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

    def _models_status(self) -> dict[str, Any]:
        status = inspect_model_status(self.services.root)
        return {
            "status": status.status,
            "active_model_profile": status.active_model_profile,
            "active_provider": status.active_provider,
            "active_model": status.active_model,
            "provider_kind": status.provider_kind,
            "api_key_env": status.api_key_env,
            "warnings": status.warnings,
            "usage": status.usage.model_dump(mode="json"),
            "secret_values_exposed": False,
        }

    def _usage_summary(self) -> dict[str, Any]:
        summary = UsageStore(self.services.root).summary()
        return {"summary": summary.model_dump(mode="json")}

    def _agents_status(self) -> dict[str, Any]:
        agents = AgentRuntimeRegistry(self.services.root).list_agents()
        active_count = sum(1 for agent in agents if agent.status in ACTIVE_STATUSES)
        return {
            "active_count": active_count,
            "total_count": len(agents),
            "agents": [_agent_payload(agent) for agent in agents],
        }


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


def _bounded_limit(value: object, *, default: int, maximum: int) -> int:
    if value is None:
        return default
    try:
        limit = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError("Expected limit to be an integer.") from error
    if limit < 1:
        raise ValueError("Limit must be at least 1.")
    return min(limit, maximum)


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
        "reason": _safe_policy_reason(result),
        "matched_rule": result.matched_rule,
        "rule_type": result.rule_type,
    }


def _agent_payload(agent) -> dict[str, Any]:
    return {
        "id": agent.id,
        "name": agent.name,
        "kind": agent.kind.value,
        "status": agent.status.value,
        "role": agent.role,
        "model_profile": agent.model_profile,
        "effort": agent.effort,
        "parent_id": agent.parent_id,
        "current_task_excerpt": _safe_excerpt(agent.current_task),
        "started_at": agent.started_at,
        "updated_at": agent.updated_at,
        "input_tokens": agent.input_tokens,
        "output_tokens": agent.output_tokens,
        "estimated_cost_usd": agent.estimated_cost_usd,
    }


def _safe_policy_reason(result) -> str:
    rule_type = result.rule_type or "request"
    if rule_type == "sensitive_path":
        subject = "sensitive path"
    elif rule_type in {"destructive_command", "approval_command", "command"}:
        subject = "command"
    elif rule_type == "path":
        subject = "path"
    else:
        subject = "request"

    severity = result.severity.value
    if severity == "block":
        return f"Blocked {subject}."
    if severity == "warn":
        return f"{subject.capitalize()} requires explicit approval."
    return f"Allowed {subject}."


def _safe_excerpt(value: str, limit: int = 160) -> str:
    redacted = safe_report_text(value)
    normalized = " ".join(redacted.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."
