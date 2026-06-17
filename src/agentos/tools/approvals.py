from __future__ import annotations

from agentos.tools.schemas import ToolDefinition, ToolRiskLevel


def requires_approval(tool: ToolDefinition) -> bool:
    return tool.requires_approval or tool.risk_level == ToolRiskLevel.REVIEW


def is_approved(tool: ToolDefinition, approvals: set[str]) -> bool:
    return tool.name in approvals
