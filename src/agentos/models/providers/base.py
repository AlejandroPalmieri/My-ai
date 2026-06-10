from __future__ import annotations

from typing import Protocol

from agentos.models.schemas import ChatRequest, ChatResponse, ModelProfile, ModelProvider


class ChatProvider(Protocol):
    def complete(
        self,
        request: ChatRequest,
        provider: ModelProvider,
        profile: ModelProfile,
    ) -> ChatResponse: ...


def approximate_tokens(*parts: str | None) -> int:
    text = " ".join(part for part in parts if part)
    if not text.strip():
        return 0
    return max(1, (len(text) + 3) // 4)
