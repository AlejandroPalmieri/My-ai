from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol

from agentos.models.schemas import (
    ChatRequest,
    ChatResponse,
    ChatStreamEvent,
    ModelProfile,
    ModelProvider,
)


class ChatProvider(Protocol):
    supports_streaming: bool

    def complete(
        self,
        request: ChatRequest,
        provider: ModelProvider,
        profile: ModelProfile,
    ) -> ChatResponse: ...

    def stream(
        self,
        request: ChatRequest,
        provider: ModelProvider,
        profile: ModelProfile,
    ) -> Iterator[ChatStreamEvent]: ...


def approximate_tokens(*parts: str | None) -> int:
    text = " ".join(part for part in parts if part)
    if not text.strip():
        return 0
    return max(1, (len(text) + 3) // 4)
