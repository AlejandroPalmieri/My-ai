import os

import httpx

from agentos.models.config import default_model_config
from agentos.models.providers.anthropic import AnthropicProvider
from agentos.models.providers.factory import provider_adapter
from agentos.models.providers.local_stub import LocalStubProvider
from agentos.models.providers.ollama import OllamaProvider
from agentos.models.providers.openai import OpenAIProvider
from agentos.models.providers.openai_compatible import OpenAICompatibleProvider
from agentos.models.providers.openrouter import OpenRouterProvider
from agentos.models.schemas import ChatRequest, ModelProvider


def test_provider_factory_selection():
    providers = {provider.name: provider for provider in default_model_config().providers}

    assert isinstance(provider_adapter(providers["local"]), LocalStubProvider)
    assert isinstance(provider_adapter(providers["openai"]), OpenAIProvider)
    assert isinstance(provider_adapter(providers["openrouter"]), OpenRouterProvider)
    assert isinstance(provider_adapter(providers["anthropic"]), AnthropicProvider)
    assert isinstance(provider_adapter(providers["ollama"]), OllamaProvider)


def test_missing_api_key_behavior(monkeypatch):
    config = default_model_config()
    provider = next(provider for provider in config.providers if provider.name == "openai")
    profile = next(profile for profile in config.model_profiles if profile.provider == "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    response = provider_adapter(provider).chat(ChatRequest(message="hello"), provider, profile)

    assert response.status == "not configured"
    assert response.error_code == "missing_api_key"
    assert "OPENAI_API_KEY" in response.text


def test_local_stub_works_and_supports_streaming():
    config = default_model_config()
    provider = next(provider for provider in config.providers if provider.name == "local")
    profile = next(profile for profile in config.model_profiles if profile.provider == "local")
    adapter = provider_adapter(provider)

    response = adapter.chat(ChatRequest(message="hello"), provider, profile)
    events = list(adapter.stream_chat(ChatRequest(message="hello"), provider, profile))

    assert response.status == "ok"
    assert adapter.supports_streaming is True
    assert any(event.type == "content_delta" for event in events)


def test_provider_config_validation(monkeypatch):
    config = default_model_config()
    provider = next(provider for provider in config.providers if provider.name == "openrouter")
    profile = next(profile for profile in config.model_profiles if profile.provider == "openrouter")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    detail = provider_adapter(provider).validate_config(provider, profile)

    assert detail is not None
    assert "OPENROUTER_API_KEY" in detail


def test_error_normalization():
    adapter = OpenAICompatibleProvider()

    assert adapter.normalize_error("401 Unauthorized")[0] == "auth_error"
    assert adapter.normalize_error("429 rate limit")[0] == "rate_limit"
    assert adapter.normalize_error("model not found")[0] == "invalid_model"
    assert adapter.normalize_error("connect timeout")[0] == "network_error"


def test_streaming_capability_detection():
    config = default_model_config()

    assert {provider.name: provider.supports_streaming for provider in config.providers} == {
        "local": True,
        "openai": True,
        "anthropic": True,
        "openrouter": True,
        "ollama": True,
    }


def test_openai_compatible_mock_http_response(monkeypatch):
    provider = ModelProvider(
        name="compatible",
        kind="openai_compatible",
        base_url="https://example.test/v1",
        api_key_env="COMPATIBLE_API_KEY",
        supports_streaming=True,
    )
    profile = default_model_config().model_profiles[0].model_copy(
        update={"provider": "compatible", "model": "compatible-model"}
    )
    monkeypatch.setenv("COMPATIBLE_API_KEY", "secret-value")

    def fake_post(*args, **kwargs):
        assert kwargs["headers"]["Authorization"] == "Bearer secret-value"
        return httpx.Response(
            200,
            request=httpx.Request("POST", "https://example.test/v1/chat/completions"),
            json={
                "choices": [{"message": {"content": "mocked"}}],
                "usage": {"prompt_tokens": 2, "completion_tokens": 3},
            },
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    response = OpenAICompatibleProvider().chat(ChatRequest(message="hello"), provider, profile)

    assert response.text == "mocked"
    assert response.usage.total_tokens == 5


def test_ollama_unavailable_gives_friendly_error(monkeypatch):
    config = default_model_config()
    provider = next(provider for provider in config.providers if provider.name == "ollama")
    profile = next(profile for profile in config.model_profiles if profile.provider == "ollama")

    def fake_post(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "post", fake_post)

    response = OllamaProvider().chat(ChatRequest(message="hello"), provider, profile)

    assert response.error_code == "network_error"
    assert "Ollama is not reachable" in response.text


def test_openrouter_safe_headers_do_not_include_secret(monkeypatch):
    config = default_model_config()
    provider = next(provider for provider in config.providers if provider.name == "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "secret-value")

    headers = OpenRouterProvider().headers(provider, os.environ["OPENROUTER_API_KEY"])

    assert headers["Authorization"] == "Bearer secret-value"
    assert "HTTP-Referer" in headers
