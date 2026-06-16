from __future__ import annotations

from agentos.models.providers.anthropic import AnthropicProvider
from agentos.models.providers.base import ProviderAdapter
from agentos.models.providers.local_stub import LocalStubProvider
from agentos.models.providers.ollama import OllamaProvider
from agentos.models.providers.openai import OpenAIProvider
from agentos.models.providers.openai_compatible import OpenAICompatibleProvider
from agentos.models.providers.openrouter import OpenRouterProvider
from agentos.models.schemas import ModelProvider


def provider_adapter(provider: ModelProvider) -> ProviderAdapter:
    if provider.kind == "local_stub":
        return LocalStubProvider()
    if provider.kind == "openai":
        return OpenAIProvider()
    if provider.kind == "openrouter" or provider.name == "openrouter":
        return OpenRouterProvider()
    if provider.kind == "anthropic":
        return AnthropicProvider()
    if provider.kind == "ollama":
        return OllamaProvider()
    return OpenAICompatibleProvider()
