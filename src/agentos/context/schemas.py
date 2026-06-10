from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ContextStatus = Literal["ok", "warn", "critical", "unknown"]


class ContextUsage(BaseModel):
    model_profile: str
    context_window_tokens: int = Field(ge=0)
    estimated_input_tokens: int = Field(default=0, ge=0)
    estimated_output_tokens: int = Field(default=0, ge=0)
    reserved_output_tokens: int = Field(default=0, ge=0)
    total_estimated_tokens: int = Field(default=0, ge=0)
    used_percent: float | None = None
    status: ContextStatus = "unknown"


class ContextMessage(BaseModel):
    role: str
    content: str


class CompactionResult(BaseModel):
    messages: list[ContextMessage]
    dropped_count: int = Field(default=0, ge=0)
    notice: str | None = None
    usage: ContextUsage
