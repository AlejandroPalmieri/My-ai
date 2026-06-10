from __future__ import annotations

from agentos.models.providers.base import approximate_tokens
from agentos.models.schemas import (
    ChatRequest,
    ChatResponse,
    ChatUsage,
    ModelProfile,
    ModelProvider,
)
from agentos.models.usage import chat_usage_for_profile


class LocalStubProvider:
    def complete(
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


def zero_usage() -> ChatUsage:
    return ChatUsage(input_tokens=0, output_tokens=0, total_tokens=0, estimated_cost_usd=None)
