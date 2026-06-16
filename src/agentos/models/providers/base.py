from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any, Protocol

from agentos.models.schemas import (
    ChatRequest,
    ChatResponse,
    ChatStreamEvent,
    ChatUsage,
    ModelProfile,
    ModelProvider,
    ProviderErrorCode,
)
from agentos.models.usage import chat_usage_for_profile


class ProviderAdapter(Protocol):
    supports_streaming: bool

    def validate_config(self, provider: ModelProvider, profile: ModelProfile) -> str | None: ...

    def chat(
        self,
        request: ChatRequest,
        provider: ModelProvider,
        profile: ModelProfile,
    ) -> ChatResponse: ...

    def stream_chat(
        self,
        request: ChatRequest,
        provider: ModelProvider,
        profile: ModelProfile,
    ) -> Iterator[ChatStreamEvent]: ...

    def estimate_or_parse_usage(
        self,
        data: dict[str, Any] | None,
        request: ChatRequest,
        response_text: str,
        profile: ModelProfile,
    ) -> ChatUsage: ...

    def normalize_error(self, error: object) -> tuple[ProviderErrorCode, str]: ...


class BaseProviderAdapter:
    supports_streaming = False

    def validate_config(self, provider: ModelProvider, profile: ModelProfile) -> str | None:
        if provider.api_key_env and not os.environ.get(provider.api_key_env):
            return (
                f"Model provider '{provider.name}' is not configured. Set "
                f"{provider.api_key_env} in your environment, then rerun the command. "
                "AgentOS does not read .env automatically."
            )
        return None

    def complete(
        self,
        request: ChatRequest,
        provider: ModelProvider,
        profile: ModelProfile,
    ) -> ChatResponse:
        return self.chat(request, provider, profile)

    def stream(
        self,
        request: ChatRequest,
        provider: ModelProvider,
        profile: ModelProfile,
    ) -> Iterator[ChatStreamEvent]:
        return self.stream_chat(request, provider, profile)

    def stream_chat(
        self,
        request: ChatRequest,
        provider: ModelProvider,
        profile: ModelProfile,
    ) -> Iterator[ChatStreamEvent]:
        yield ChatStreamEvent(type="error", error="Provider does not support streaming.")

    def estimate_or_parse_usage(
        self,
        data: dict[str, Any] | None,
        request: ChatRequest,
        response_text: str,
        profile: ModelProfile,
    ) -> ChatUsage:
        usage = (data or {}).get("usage")
        if isinstance(usage, dict):
            input_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
            output_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
            if input_tokens or output_tokens:
                return chat_usage_for_profile(
                    profile,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
        return chat_usage_for_profile(
            profile,
            input_tokens=approximate_tokens(request.system_prompt, request.message),
            output_tokens=approximate_tokens(response_text),
        )

    def normalize_error(self, error: object) -> tuple[ProviderErrorCode, str]:
        text = str(error)
        lowered = text.lower()
        if "401" in lowered or "unauthorized" in lowered or "forbidden" in lowered:
            return (
                "auth_error",
                "Provider authentication failed. Check the configured API key env var.",
            )
        if "429" in lowered or "rate limit" in lowered:
            return "rate_limit", "Provider rate limit reached. Try again later."
        if "404" in lowered or "model" in lowered and "not found" in lowered:
            return "invalid_model", "Provider rejected the configured model name."
        if "connect" in lowered or "timeout" in lowered or "network" in lowered:
            return "network_error", "Provider network request failed."
        return "provider_error", text

    def setup_response(
        self,
        request: ChatRequest,
        provider: ModelProvider,
        profile: ModelProfile,
        message: str,
        *,
        code: ProviderErrorCode = "provider_error",
    ) -> ChatResponse:
        status = "not configured" if code == "missing_api_key" else code
        return ChatResponse(
            status=status,
            text=message,
            provider=provider.name,
            provider_kind=provider.kind,
            model_profile=profile.name,
            model=profile.model,
            effort=request.effort or profile.effort,
            usage=ChatUsage(),
            error=message,
            error_code=code,
        )


def approximate_tokens(*parts: str | None) -> int:
    text = " ".join(part for part in parts if part)
    if not text.strip():
        return 0
    return max(1, (len(text) + 3) // 4)


def safe_headers(provider: ModelProvider) -> dict[str, str]:
    blocked = {"authorization", "api-key", "x-api-key", "cookie"}
    return {
        key: value
        for key, value in provider.extra_headers.items()
        if key.strip().lower() not in blocked
    }
