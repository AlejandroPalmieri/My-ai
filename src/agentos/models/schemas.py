from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ModelProviderKind = Literal[
    "openai_compatible",
    "openai",
    "anthropic",
    "ollama",
    "local_stub",
]
ModelEffort = Literal["low", "medium", "high", "max"]


class ModelProvider(BaseModel):
    name: str
    kind: ModelProviderKind
    base_url: str | None = None
    api_key_env: str | None = None
    enabled: bool = True
    supports_streaming: bool = False


class ModelProfile(BaseModel):
    name: str
    provider: str
    model: str
    effort: ModelEffort = "medium"
    context_window_tokens: int = Field(ge=0)
    input_token_cost_per_1m: float | None = None
    output_token_cost_per_1m: float | None = None
    default_temperature: float = 0.2
    enabled: bool = True


class ActiveModelState(BaseModel):
    active_model_profile: str
    active_provider: str
    active_model: str
    effort: ModelEffort
    context_window_tokens: int = Field(ge=0)
    context_used_tokens: int = Field(default=0, ge=0)
    context_used_percent: float = 0.0
    cumulative_input_tokens: int = Field(default=0, ge=0)
    cumulative_output_tokens: int = Field(default=0, ge=0)
    cumulative_total_tokens: int = Field(default=0, ge=0)
    cumulative_estimated_cost_usd: float | None = None


class ModelConfig(BaseModel):
    active: ActiveModelState
    providers: list[ModelProvider]
    model_profiles: list[ModelProfile]


class ModelProviderStatus(BaseModel):
    active_model_profile: str
    active_provider: str
    active_model: str
    provider_kind: ModelProviderKind
    status: str
    api_key_env: str | None = None
    warnings: list[str] = Field(default_factory=list)
    usage: ActiveModelState


class ChatUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float | None = None


class ChatRequest(BaseModel):
    message: str
    system_prompt: str | None = None
    model_profile_name: str | None = None
    effort: ModelEffort | None = None


class ChatResponse(BaseModel):
    status: str = "ok"
    text: str
    provider: str
    provider_kind: ModelProviderKind
    model_profile: str
    model: str
    effort: ModelEffort
    usage: ChatUsage
    error: str | None = None
    streamed: bool = False
    stream_fallback: bool = False


StreamEventType = Literal[
    "message_start",
    "content_delta",
    "message_done",
    "usage_delta",
    "error",
]


class ChatStreamEvent(BaseModel):
    type: StreamEventType
    delta: str = ""
    usage: ChatUsage | None = None
    error: str | None = None
