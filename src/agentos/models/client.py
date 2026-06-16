from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

from agentos.logging.traces import TraceEventType, TraceLogger
from agentos.models.config import (
    create_default_model_config,
    read_model_config,
    set_active_model_profile,
)
from agentos.models.providers.base import approximate_tokens
from agentos.models.providers.local_stub import LocalStubProvider
from agentos.models.providers.openai_compatible import OpenAICompatibleProvider
from agentos.models.routing import effective_effort, effective_model_profile
from agentos.models.schemas import (
    ChatRequest,
    ChatResponse,
    ChatUsage,
    ModelProfile,
    ModelProvider,
)
from agentos.models.usage import chat_usage_for_profile, record_model_usage


def chat_once(
    root: Path,
    *,
    message: str,
    model_profile_name: str | None = None,
    effort: str | None = None,
    system_prompt: str | None = None,
    session_id: str | None = None,
    agent_id: str | None = None,
    stream: bool = False,
    on_delta: Callable[[str], None] | None = None,
) -> ChatResponse:
    path = create_default_model_config(root)
    routed_model_profile = effective_model_profile(root, "default_chat", model_profile_name)
    if routed_model_profile:
        config = set_active_model_profile(root, routed_model_profile)
    else:
        config = read_model_config(path)
    profile = _profile_by_name(config.model_profiles, config.active.active_model_profile)
    provider = _provider_by_name(config.providers, profile.provider)
    effort_value = effective_effort(root, "default_chat", effort)
    request = ChatRequest(
        message=message,
        system_prompt=system_prompt,
        model_profile_name=profile.name,
        effort=effort_value,
    )
    trace = TraceLogger(root)
    trace.log_event(
        TraceEventType.MODEL_REQUEST_STARTED,
        command="chat.once",
        status="started",
        payload={
            "provider": provider.name,
            "model_profile": profile.name,
            "model": profile.model,
            "effort": request.effort or profile.effort,
        },
    )
    client = _provider_client(provider)
    can_stream = getattr(client, "supports_streaming", False) and _provider_supports_streaming(
        provider
    )
    if stream and can_stream:
        response = _complete_streaming(client, request, provider, profile, trace, on_delta)
    else:
        response = client.complete(request, provider, profile)
        response.stream_fallback = stream
    if response.status == "ok":
        _, usage_event = record_model_usage(
            root,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            provider=response.provider,
            model=response.model,
            effort=response.effort,
            command="chat.once",
            session_id=session_id or uuid4().hex,
            agent_id=agent_id,
        )
        trace.log_event(
            TraceEventType.MODEL_REQUEST_COMPLETED,
            command="chat.once",
            status="ok",
            payload=_trace_payload(
                response,
                usage_event_id=usage_event.id if usage_event else None,
            ),
        )
        trace.log_event(
            TraceEventType.MODEL_USAGE_UPDATED,
            command="chat.once",
            status="ok",
            payload={
                "provider": response.provider,
                "model_profile": response.model_profile,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.total_tokens,
                "estimated_cost_usd": response.usage.estimated_cost_usd,
                "usage_event_id": usage_event.id if usage_event else None,
            },
        )
        return response
    trace.log_event(
        TraceEventType.MODEL_REQUEST_FAILED,
        command="chat.once",
        status=response.status,
        payload=_trace_payload(response),
        error=response.error,
    )
    return response


def _complete_streaming(
    client,
    request: ChatRequest,
    provider: ModelProvider,
    profile: ModelProfile,
    trace: TraceLogger,
    on_delta: Callable[[str], None] | None,
) -> ChatResponse:
    trace.log_event(
        TraceEventType.STREAM_STARTED,
        command="chat.once",
        status="started",
        payload={"provider": provider.name, "model_profile": profile.name, "model": profile.model},
    )
    chunks: list[str] = []
    usage: ChatUsage | None = None
    for event in client.stream(request, provider, profile):
        if event.type == "content_delta":
            chunks.append(event.delta)
            if on_delta:
                on_delta(event.delta)
            trace.log_event(
                TraceEventType.STREAM_DELTA_RECEIVED,
                command="chat.once",
                status="delta",
                payload={
                    "provider": provider.name,
                    "model_profile": profile.name,
                    "delta_chars": len(event.delta),
                },
            )
        elif event.type == "usage_delta" and event.usage:
            usage = event.usage
        elif event.type == "error":
            error = event.error or "Streaming failed."
            trace.log_event(
                TraceEventType.STREAM_FAILED,
                command="chat.once",
                status="failed",
                payload={"provider": provider.name, "model_profile": profile.name},
                error=error,
            )
            return ChatResponse(
                status="not configured" if "not configured" in error else "error",
                text=error,
                provider=provider.name,
                provider_kind=provider.kind,
                model_profile=profile.name,
                model=profile.model,
                effort=request.effort or profile.effort,
                usage=ChatUsage(),
                error=error,
                streamed=True,
            )
    text = "".join(chunks)
    if usage is None or usage.total_tokens == 0:
        usage = chat_usage_for_profile(
            profile,
            input_tokens=approximate_tokens(request.system_prompt, request.message),
            output_tokens=approximate_tokens(text),
        )
    trace.log_event(
        TraceEventType.STREAM_COMPLETED,
        command="chat.once",
        status="ok",
        payload={
            "provider": provider.name,
            "model_profile": profile.name,
            "output_tokens": usage.output_tokens,
            "total_tokens": usage.total_tokens,
        },
    )
    return ChatResponse(
        text=text,
        provider=provider.name,
        provider_kind=provider.kind,
        model_profile=profile.name,
        model=profile.model,
        effort=request.effort or profile.effort,
        usage=usage,
        streamed=True,
    )


def _provider_client(provider: ModelProvider):
    if provider.kind == "local_stub":
        return LocalStubProvider()
    if provider.kind in {"openai_compatible", "openai"}:
        return OpenAICompatibleProvider()
    return OpenAICompatibleProvider()


def _provider_supports_streaming(provider: ModelProvider) -> bool:
    return provider.supports_streaming or provider.kind in {
        "local_stub",
        "openai",
        "openai_compatible",
    }


def _profile_by_name(profiles: list[ModelProfile], name: str) -> ModelProfile:
    for profile in profiles:
        if profile.name == name:
            return profile
    raise KeyError(f"Unknown model profile: {name}")


def _provider_by_name(providers: list[ModelProvider], name: str) -> ModelProvider:
    for provider in providers:
        if provider.name == name:
            return provider
    raise KeyError(f"Unknown model provider: {name}")


def _trace_payload(
    response: ChatResponse,
    *,
    usage_event_id: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "provider": response.provider,
        "provider_kind": response.provider_kind,
        "model_profile": response.model_profile,
        "model": response.model,
        "effort": response.effort,
        "status": response.status,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "total_tokens": response.usage.total_tokens,
    }
    if usage_event_id:
        payload["usage_event_id"] = usage_event_id
    return payload
