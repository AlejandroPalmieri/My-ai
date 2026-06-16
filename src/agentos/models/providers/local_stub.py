from __future__ import annotations

from agentos.models.providers.base import BaseProviderAdapter, approximate_tokens
from agentos.models.schemas import (
    ChatRequest,
    ChatResponse,
    ChatStreamEvent,
    ChatUsage,
    ModelProfile,
    ModelProvider,
)
from agentos.models.usage import chat_usage_for_profile


class LocalStubProvider(BaseProviderAdapter):
    supports_streaming = True

    def validate_config(self, provider: ModelProvider, profile: ModelProfile) -> str | None:
        return None

    def chat(
        self,
        request: ChatRequest,
        provider: ModelProvider,
        profile: ModelProfile,
    ) -> ChatResponse:
        effort = request.effort or profile.effort
        response_text = (
            f"local-stub response [{profile.name}/{profile.model}/{effort}]: "
            f"{request.message}"
        )
        input_tokens = approximate_tokens(request.system_prompt, request.message)
        output_tokens = approximate_tokens(response_text)
        usage = chat_usage_for_profile(
            profile,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        return ChatResponse(
            text=response_text,
            provider=provider.name,
            provider_kind=provider.kind,
            model_profile=profile.name,
            model=profile.model,
            effort=effort,
            usage=usage,
        )

    def stream_chat(
        self,
        request: ChatRequest,
        provider: ModelProvider,
        profile: ModelProfile,
    ):
        response = self.chat(request, provider, profile)
        yield ChatStreamEvent(type="message_start")
        for chunk in _deterministic_chunks(response.text):
            yield ChatStreamEvent(type="content_delta", delta=chunk)
        yield ChatStreamEvent(type="usage_delta", usage=response.usage)
        yield ChatStreamEvent(type="message_done")


def zero_usage() -> ChatUsage:
    return ChatUsage(input_tokens=0, output_tokens=0, total_tokens=0, estimated_cost_usd=None)


def _deterministic_chunks(text: str) -> list[str]:
    words = text.split(" ")
    chunks = []
    for index, word in enumerate(words):
        suffix = " " if index < len(words) - 1 else ""
        chunks.append(word + suffix)
    return chunks
