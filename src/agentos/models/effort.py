from __future__ import annotations

from pydantic import BaseModel, Field

from agentos.models.schemas import ModelEffort


class EffortProfile(BaseModel):
    label: ModelEffort
    description: str
    default_temperature: float = Field(ge=0)
    default_max_output_tokens: int = Field(gt=0)
    reasoning_budget_hint: str
    intended_use: str


EFFORT_PROFILES: dict[ModelEffort, EffortProfile] = {
    "low": EffortProfile(
        label="low",
        description="Fast, cheap, simple task handling.",
        default_temperature=0.1,
        default_max_output_tokens=800,
        reasoning_budget_hint="minimal",
        intended_use="Simple chat, quick summaries, and low-risk status checks.",
    ),
    "medium": EffortProfile(
        label="medium",
        description="Balanced default for normal planning and chat.",
        default_temperature=0.2,
        default_max_output_tokens=1600,
        reasoning_budget_hint="standard",
        intended_use="Normal planning, interactive chat, and routine CLI assistance.",
    ),
    "high": EffortProfile(
        label="high",
        description="Deeper reasoning for architecture, code review, and multi-step work.",
        default_temperature=0.2,
        default_max_output_tokens=3200,
        reasoning_budget_hint="extended",
        intended_use="Architecture, code review, multi-step reasoning, and coding tasks.",
    ),
    "max": EffortProfile(
        label="max",
        description="Maximum local reasoning hint for difficult design and verification.",
        default_temperature=0.1,
        default_max_output_tokens=6400,
        reasoning_budget_hint="maximum",
        intended_use="Difficult design, debugging, safety review, and final verification.",
    ),
}


def get_effort_profile(effort: str) -> EffortProfile:
    try:
        return EFFORT_PROFILES[ModelEffortValue(effort)]
    except (KeyError, ValueError) as error:
        raise KeyError(f"Unknown effort level: {effort}") from error


def validate_effort(effort: str) -> ModelEffort:
    if effort not in EFFORT_PROFILES:
        raise ValueError(f"Unknown effort level: {effort}")
    return ModelEffortValue(effort)


def ModelEffortValue(value: str) -> ModelEffort:
    if value not in {"low", "medium", "high", "max"}:
        raise ValueError(value)
    return value  # type: ignore[return-value]
