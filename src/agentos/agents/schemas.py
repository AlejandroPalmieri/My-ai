from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class AgentKind(StrEnum):
    AGENT = "agent"
    SUBAGENT = "subagent"


class AgentStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentRecord(BaseModel):
    id: str
    name: str
    role: str
    kind: AgentKind = AgentKind.AGENT
    status: AgentStatus = AgentStatus.RUNNING
    model_profile: str
    effort: str = "low"
    parent_id: str | None = None
    current_task: str
    started_at: str
    updated_at: str
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    estimated_cost_usd: float | None = None


class AgentRuntimeState(BaseModel):
    agents: list[AgentRecord] = Field(default_factory=list)
