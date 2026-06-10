from __future__ import annotations

import os
from typing import Any

from agentos.models.providers.base import approximate_tokens
from agentos.models.schemas import (
    ChatRequest,
    ChatResponse,
    ChatUsage,
    ModelProfile,
    ModelProvider,
)
from agentos.models.usage import chat_usage_for_profile


class OpenAICompatibleProvider:
    def complete(
        self,
        request: ChatRequest,
        provider: ModelProvider,
        profile: ModelProfile,
    ) -> ChatResponse:
        if not provider.api_key_env:
            return _setup_response(
                request,
                provider,
                profile,
                "Provider has no api_key_env configured.",
            )
        api_key = os.environ.get(provider.api_key_env)
        if not api_key:
            return _setup_response(
                request,
                provider,
                profile,
                (
                    f"Model provider '{provider.name}' is not configured. Set "
                    f"{provider.api_key_env} in your environment, then rerun the command. "
                    "AgentOS does not read .env automatically."
                ),
            )
        if not provider.base_url:
            return _setup_response(
                request,
                provider,
                profile,
                "Provider has no base_url configured.",
            )

        try:
            import httpx
        except ImportError:
            return _setup_response(
                request,
                provider,
                profile,
                "httpx is not installed. Run `python -m pip install -e .` to install dependencies.",
            )

        messages: list[dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.message})
        payload: dict[str, Any] = {
            "model": profile.model,
            "messages": messages,
            "temperature": profile.default_temperature,
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        try:
            response = httpx.post(
                f"{provider.base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers=headers,
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as error:
            return _setup_response(
                request,
                provider,
                profile,
                f"OpenAI-compatible request failed: {_redact_secret(str(error), api_key)}",
            )

        text = _extract_text(data)
        usage = _usage_from_response(data, request, text, profile)
        return ChatResponse(
            text=text,
            provider=provider.name,
            provider_kind=provider.kind,
            model_profile=profile.name,
            model=profile.model,
            effort=request.effort or profile.effort,
            usage=usage,
        )


def _setup_response(
    request: ChatRequest,
    provider: ModelProvider,
    profile: ModelProfile,
    message: str,
) -> ChatResponse:
    return ChatResponse(
        status="not configured",
        text=message,
        provider=provider.name,
        provider_kind=provider.kind,
        model_profile=profile.name,
        model=profile.model,
        effort=request.effort or profile.effort,
        usage=ChatUsage(),
        error=message,
    )


def _extract_text(data: dict[str, Any]) -> str:
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


def _usage_from_response(
    data: dict[str, Any],
    request: ChatRequest,
    response_text: str,
    profile: ModelProfile,
) -> ChatUsage:
    usage = data.get("usage")
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


def _redact_secret(value: str, secret: str) -> str:
    return value.replace(secret, "[REDACTED]") if secret else value
