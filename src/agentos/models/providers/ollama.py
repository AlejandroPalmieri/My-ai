from __future__ import annotations

from typing import Any

from agentos.models.providers.openai_compatible import OpenAICompatibleProvider
from agentos.models.schemas import (
    ChatRequest,
    ChatResponse,
    ChatStreamEvent,
    ModelProfile,
    ModelProvider,
)


class OllamaProvider(OpenAICompatibleProvider):
    supports_streaming = True
    default_base_url = "http://localhost:11434/v1"
    default_api_key_env = None

    def validate_config(self, provider: ModelProvider, profile: ModelProfile) -> str | None:
        return None

    def headers(self, provider: ModelProvider, api_key: str) -> dict[str, str]:
        return {"Content-Type": "application/json"}

    def chat(
        self,
        request: ChatRequest,
        provider: ModelProvider,
        profile: ModelProfile,
    ) -> ChatResponse:
        response = super().chat(request, provider, profile)
        if response.error_code == "network_error":
            message = (
                "Ollama is not reachable. Start Ollama locally and confirm "
                f"{provider.base_url or self.default_base_url} is available."
            )
            return self.setup_response(request, provider, profile, message, code="network_error")
        return response

    def stream_chat(self, request: ChatRequest, provider: ModelProvider, profile: ModelProfile):
        for event in super().stream_chat(request, provider, profile):
            if event.type == "error":
                yield ChatStreamEvent(
                    type="error",
                    error=(
                        "Ollama streaming is not reachable. Start Ollama locally and retry."
                    ),
                )
                return
            yield event

    def payload(
        self,
        request: ChatRequest,
        profile: ModelProfile,
        *,
        stream: bool,
    ) -> dict[str, Any]:
        payload = super().payload(request, profile, stream=stream)
        payload["model"] = profile.model
        return payload
