from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentos.logging.traces import TraceEventType, TraceLogger
from agentos.policies.checker import PolicyChecker, PolicySeverity, create_default_policies
from agentos.tools.approvals import is_approved, requires_approval
from agentos.tools.registry import ToolRegistry
from agentos.tools.schemas import ToolCall, ToolExecutionContext, ToolResult, ToolRiskLevel


class ToolExecutor:
    def __init__(
        self,
        root: Path,
        registry: ToolRegistry,
        trace: TraceLogger | None = None,
    ) -> None:
        self.root = root
        self.registry = registry
        self.trace = trace or TraceLogger(root)
        create_default_policies(root)
        self.policy_checker = PolicyChecker.from_directory(root / "policies")

    def execute(self, call: ToolCall, context: ToolExecutionContext | None = None) -> ToolResult:
        context = context or ToolExecutionContext()
        self.trace.log_event(
            TraceEventType.TOOL_CALL_REQUESTED,
            command="tools.execute",
            status="requested",
            payload={"tool_name": call.name},
        )
        try:
            tool = self.registry.get(call.name)
        except KeyError as error:
            return self._blocked(call.name, str(error))

        if tool.risk_level == ToolRiskLevel.BLOCKED:
            return self._blocked(call.name, "Tool is marked blocked.")
        if context.call_counts.get(tool.name, 0) >= tool.max_calls_per_run:
            return self._blocked(call.name, "Tool max_calls_per_run exceeded.")
        validation_error = _validate_required(call.arguments, tool.input_schema)
        if validation_error:
            return self._blocked(call.name, validation_error)
        policy_error = None if call.name == "policies_check" else self._policy_error(call.arguments)
        if policy_error:
            return self._blocked(call.name, policy_error)
        if requires_approval(tool) and not is_approved(tool, context.approvals):
            return self._blocked(
                call.name,
                "Tool requires explicit approval.",
                requires_approval=True,
            )

        self.trace.log_event(
            TraceEventType.TOOL_CALL_ALLOWED,
            command="tools.execute",
            status="allowed",
            payload={"tool_name": call.name},
        )
        try:
            output = self.registry.handler(tool.name)(self.root, call.arguments)
        except Exception as error:
            self.trace.log_event(
                TraceEventType.TOOL_CALL_FAILED,
                command="tools.execute",
                status="failed",
                payload={"tool_name": call.name},
                error=str(error),
            )
            return ToolResult(tool_name=call.name, status="failed", error=str(error))

        context.call_counts[tool.name] = context.call_counts.get(tool.name, 0) + 1
        self.trace.log_event(
            TraceEventType.TOOL_CALL_COMPLETED,
            command="tools.execute",
            status="completed",
            payload={"tool_name": call.name},
        )
        return ToolResult(tool_name=call.name, status="ok", output=_redact_output(output))

    def _blocked(
        self,
        tool_name: str,
        reason: str,
        *,
        requires_approval: bool = False,
    ) -> ToolResult:
        self.trace.log_event(
            TraceEventType.TOOL_CALL_BLOCKED,
            command="tools.execute",
            status="blocked",
            payload={"tool_name": tool_name, "requires_approval": requires_approval},
            error=reason,
        )
        return ToolResult(
            tool_name=tool_name,
            status="blocked",
            error=reason,
            requires_approval=requires_approval,
        )

    def _policy_error(self, arguments: dict[str, Any]) -> str | None:
        text = json.dumps(arguments, sort_keys=True)
        command_result = self.policy_checker.check_command(text)
        if command_result.severity == PolicySeverity.BLOCK:
            return command_result.reason
        for value in _iter_strings(arguments):
            path_result = self.policy_checker.check_path(value)
            if path_result.severity == PolicySeverity.BLOCK:
                return path_result.reason
        return None


def _validate_required(arguments: dict[str, Any], input_schema: dict[str, Any]) -> str | None:
    for key in input_schema.get("required", []):
        value = arguments.get(key)
        if value is None or str(value).strip() == "":
            return f"Missing required argument: {key}"
    return None


def _iter_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _iter_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_strings(child)


def _redact_output(output: dict[str, Any]) -> dict[str, Any]:
    for value in _iter_strings(output):
        text = value.lower()
        if any(marker in text for marker in (".env", ".ssh", "api_key", "token", "secret")):
            return {"redacted": True}
    return output
