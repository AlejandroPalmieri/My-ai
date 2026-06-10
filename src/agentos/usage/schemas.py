from __future__ import annotations

from pydantic import BaseModel, Field


class UsageEvent(BaseModel):
    id: str
    timestamp: str
    session_id: str
    project: str
    profile: str
    provider: str
    model: str
    effort: str
    agent_id: str | None = None
    command: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    estimated_cost_usd: float | None = None
    context_used_percent: float | None = None


class UsageSummary(BaseModel):
    key: str
    event_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float | None = None
    session_id: str | None = None
    usage_date: str | None = None
    project: str | None = None
    profile: str | None = None
    provider: str | None = None
    model: str | None = None
    agent_id: str | None = None
