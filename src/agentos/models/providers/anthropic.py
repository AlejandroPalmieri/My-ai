from __future__ import annotations

import json
import os
from typing import Any

from agentos.models.providers.base import BaseProviderAdapter
from agentos.models.schemas import (
    ChatRequest,
    ChatResponse,
    ChatStreamEvent,
    ModelProfile,
    ModelProvider,
)


class AnthropicProvider(BaseProviderAdapter):
    supports_streaming = True
    default_base_url = "https://api.anthropic.com/v1"
    default_api_key_env = "ANTHROPIC_API_KEY"

    def validate_config(self, provider: ModelProvider, profile: ModelProfile) -> str | None:
        env_name = provider.api_key_env or self.default_api_key_env
        if not os.environ.get(env_name):
            return (
                f"Model provider '{provider.name}' is not configured. Set {env_name} in "
                "your environment. AgentOS does not read .env automatically."
            )
        return None

    def chat(
        self,
        request: ChatRequest,
        provider: ModelProvider,
        profile: ModelProfile,
    ) -> ChatResponse:
        config_error = self.validate_config(provider, profile)
        if config_error:
            return self.setup_response(
                request,
                provider,
                profile,
                config_error,
                code="missing_api_key",
            )
        httpx = _load_httpx()
        if isinstance(httpx, str):
            return self.setup_response(request, provider, profile, httpx, code="provider_error")
        api_key = os.environ[provider.api_key_env or self.default_api_key_env]
        try:
            response = httpx.post(
                f"{(provider.base_url or self.default_base_url).rstrip('/')}/messages",
                json=self.payload(request, profile, stream=False),
                headers=self.headers(provider, api_key),
                timeout=provider.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as error:
            code, message = self.normalize_error(str(error).replace(api_key, "[REDACTED]"))
            return self.setup_response(request, provider, profile, message, code=code)
        text = self.extract_text(data)
        usage = self.estimate_or_parse_usage(data, request, text, profile)
        return ChatResponse(
            text=text,
            provider=provider.name,
            provider_kind=provider.kind,
            model_profile=profile.name,
            model=profile.model,
            effort=request.effort or profile.effort,
            usage=usage,
        )

    def stream_chat(self, request: ChatRequest, provider: ModelProvider, profile: ModelProfile):
        config_error = self.validate_config(provider, profile)
        if config_error:
            yield ChatStreamEvent(type="error", error=config_error)
            return
        httpx = _load_httpx()
        if isinstance(httpx, str):
            yield ChatStreamEvent(type="error", error=httpx)
            return
        api_key = os.environ[provider.api_key_env or self.default_api_key_env]
        yield ChatStreamEvent(type="message_start")
        try:
            with httpx.stream(
                "POST",
                f"{(provider.base_url or self.default_base_url).rstrip('/')}/messages",
                json=self.payload(request, profile, stream=True),
                headers=self.headers(provider, api_key),
                timeout=provider.timeout_seconds,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    event = self.stream_event_from_line(line, request, profile)
                    if event:
                        yield event
        except Exception as error:
            _code, message = self.normalize_error(str(error).replace(api_key, "[REDACTED]"))
            yield ChatStreamEvent(type="error", error=message)
            return
        yield ChatStreamEvent(type="message_done")

    def payload(
        self,
        request: ChatRequest,
        profile: ModelProfile,
        *,
        stream: bool,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": profile.model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": request.message}],
        }
        if request.system_prompt:
            payload["system"] = request.system_prompt
        if stream:
            payload["stream"] = True
        return payload

    def headers(self, provider: ModelProvider, api_key: str) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }

    def extract_text(self, data: dict[str, Any]) -> str:
        content = data.get("content")
        if isinstance(content, list):
            return "".join(
                item.get("text", "") for item in content if isinstance(item, dict)
            )
        return ""

    def estimate_or_parse_usage(self, data, request, response_text, profile):
        usage = (data or {}).get("usage")
        if isinstance(usage, dict):
            normalized = {
                "usage": {
                    "input_tokens": usage.get("input_tokens") or 0,
                    "output_tokens": usage.get("output_tokens") or 0,
                }
            }
            if normalized["usage"]["input_tokens"] or normalized["usage"]["output_tokens"]:
                return super().estimate_or_parse_usage(normalized, request, response_text, profile)
        return super().estimate_or_parse_usage(data, request, response_text, profile)

    def stream_event_from_line(self, line: str, request: ChatRequest, profile: ModelProfile):
        if not line or not line.startswith("data:"):
            return None
        try:
            data = json.loads(line.removeprefix("data:").strip())
        except Exception:
            return None
        if data.get("type") == "content_block_delta":
            delta = data.get("delta")
            if isinstance(delta, dict) and isinstance(delta.get("text"), str):
                return ChatStreamEvent(type="content_delta", delta=delta["text"])
        if data.get("type") == "message_delta":
            usage = self.estimate_or_parse_usage(data.get("message") or data, request, "", profile)
            if usage.total_tokens:
                return ChatStreamEvent(type="usage_delta", usage=usage)
        return None


def _load_httpx():
    try:
        import httpx
    except ImportError:
        return "httpx is required for Anthropic. Run `python -m pip install -e .`."
    return httpx
