from __future__ import annotations

import json
import os
from typing import Any

from agentos.models.providers.base import BaseProviderAdapter, safe_headers
from agentos.models.schemas import (
    ChatRequest,
    ChatResponse,
    ChatStreamEvent,
    ModelProfile,
    ModelProvider,
)


class OpenAICompatibleProvider(BaseProviderAdapter):
    supports_streaming = True
    default_base_url: str | None = None
    default_api_key_env: str | None = None

    def validate_config(self, provider: ModelProvider, profile: ModelProfile) -> str | None:
        api_key_env = provider.api_key_env or self.default_api_key_env
        if api_key_env and not os.environ.get(api_key_env):
            return (
                f"Model provider '{provider.name}' is not configured. Set "
                f"{api_key_env} in your environment, then rerun the command. "
                "AgentOS does not read .env automatically."
            )
        if not self.base_url(provider):
            return f"Model provider '{provider.name}' has no base_url configured."
        return None

    def chat(
        self,
        request: ChatRequest,
        provider: ModelProvider,
        profile: ModelProfile,
    ) -> ChatResponse:
        config_error = self.validate_config(provider, profile)
        if config_error:
            code = "missing_api_key" if "environment" in config_error else "provider_error"
            return self.setup_response(request, provider, profile, config_error, code=code)
        httpx = _load_httpx()
        if isinstance(httpx, str):
            return self.setup_response(request, provider, profile, httpx, code="provider_error")

        api_key = self.api_key(provider)
        try:
            response = httpx.post(
                f"{self.base_url(provider).rstrip('/')}/chat/completions",
                json=self.payload(request, profile, stream=False),
                headers=self.headers(provider, api_key),
                timeout=provider.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as error:
            code, message = self.normalize_error(_redact_secret(str(error), api_key))
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

    def stream_chat(
        self,
        request: ChatRequest,
        provider: ModelProvider,
        profile: ModelProfile,
    ):
        config_error = self.validate_config(provider, profile)
        if config_error:
            yield ChatStreamEvent(type="error", error=config_error)
            return
        httpx = _load_httpx()
        if isinstance(httpx, str):
            yield ChatStreamEvent(type="error", error=httpx)
            return

        api_key = self.api_key(provider)
        yield ChatStreamEvent(type="message_start")
        try:
            with httpx.stream(
                "POST",
                f"{self.base_url(provider).rstrip('/')}/chat/completions",
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
            _code, message = self.normalize_error(_redact_secret(str(error), api_key))
            yield ChatStreamEvent(type="error", error=message)
            return
        yield ChatStreamEvent(type="message_done")

    def base_url(self, provider: ModelProvider) -> str:
        return provider.base_url or self.default_base_url or ""

    def api_key_env(self, provider: ModelProvider) -> str | None:
        return provider.api_key_env or self.default_api_key_env

    def api_key(self, provider: ModelProvider) -> str:
        env_name = self.api_key_env(provider)
        return os.environ.get(env_name or "", "")

    def headers(self, provider: ModelProvider, api_key: str) -> dict[str, str]:
        headers = {"Content-Type": "application/json", **safe_headers(provider)}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def payload(
        self,
        request: ChatRequest,
        profile: ModelProfile,
        *,
        stream: bool,
    ) -> dict[str, Any]:
        messages: list[dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.message})
        payload: dict[str, Any] = {
            "model": profile.model,
            "messages": messages,
            "temperature": profile.default_temperature,
        }
        if stream:
            payload["stream"] = True
        return payload

    def extract_text(self, data: dict[str, Any]) -> str:
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message")
                if isinstance(message, dict) and isinstance(message.get("content"), str):
                    return message["content"]
                if isinstance(first.get("text"), str):
                    return first["text"]
        return ""

    def stream_event_from_line(
        self,
        line: str,
        request: ChatRequest,
        profile: ModelProfile,
    ) -> ChatStreamEvent | None:
        if not line or not line.startswith("data:"):
            return None
        payload = line.removeprefix("data:").strip()
        if payload == "[DONE]":
            return None
        try:
            data = json.loads(payload)
        except Exception:
            return None
        usage = data.get("usage")
        if isinstance(usage, dict):
            chat_usage = self.estimate_or_parse_usage(data, request, "", profile)
            if chat_usage.total_tokens:
                return ChatStreamEvent(type="usage_delta", usage=chat_usage)
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            return None
        first = choices[0]
        if not isinstance(first, dict):
            return None
        delta = first.get("delta")
        if isinstance(delta, dict) and isinstance(delta.get("content"), str):
            return ChatStreamEvent(type="content_delta", delta=delta["content"])
        if isinstance(first.get("text"), str):
            return ChatStreamEvent(type="content_delta", delta=first["text"])
        return None


def _load_httpx():
    try:
        import httpx
    except ImportError:
        return "httpx is not installed. Run `python -m pip install -e .` to install dependencies."
    return httpx


def _redact_secret(value: str, secret: str) -> str:
    return value.replace(secret, "[REDACTED]") if secret else value
