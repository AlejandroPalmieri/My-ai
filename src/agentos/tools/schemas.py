from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ToolRiskLevel(StrEnum):
    SAFE = "safe"
    REVIEW = "review"
    BLOCKED = "blocked"


class ToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    risk_level: ToolRiskLevel = ToolRiskLevel.SAFE
    requires_approval: bool = False
    max_calls_per_run: int = Field(default=5, ge=0, le=20)


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    tool_name: str
    status: str
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    requires_approval: bool = False


class ToolExecutionContext(BaseModel):
    approvals: set[str] = Field(default_factory=set)
    call_counts: dict[str, int] = Field(default_factory=dict)


class ToolProtocolMessage(BaseModel):
    tool_calls: list[ToolCall] = Field(default_factory=list)
    final_answer: str | None = None
