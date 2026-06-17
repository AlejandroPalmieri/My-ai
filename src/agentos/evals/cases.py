from __future__ import annotations

import os
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from agentos.agents.planner import AgentPlanner
from agentos.agents.tool_loop import AgentToolLoop
from agentos.brain.store import StrategicBrainStore
from agentos.context.compactor import compact_session_history
from agentos.context.estimator import estimate_context_usage
from agentos.evals.assertions import assert_equal, assert_in, assert_not_in, assert_true
from agentos.memory.store import MemoryStore
from agentos.models.client import chat_once
from agentos.models.config import inspect_model_status, write_model_config
from agentos.models.providers.factory import provider_adapter
from agentos.models.providers.local_stub import LocalStubProvider
from agentos.models.schemas import (
    ActiveModelState,
    ChatRequest,
    ModelConfig,
    ModelProfile,
    ModelProvider,
)
from agentos.policies.checker import PolicyChecker, create_default_policies
from agentos.retrieval.context_builder import build_retrieval_context
from agentos.retrieval.schemas import RetrievalSettings
from agentos.tools.builtin_tools import create_builtin_tool_registry
from agentos.tools.executor import ToolExecutor
from agentos.tools.registry import ToolRegistry
from agentos.tools.schemas import ToolCall, ToolDefinition, ToolProtocolMessage, ToolResult

PROVIDER_EVALS = "provider_evals"
STREAMING_EVALS = "streaming_evals"
CONTEXT_EVALS = "context_evals"
RETRIEVAL_EVALS = "retrieval_evals"
AGENT_RUN_EVALS = "agent_run_evals"
TOOL_CALL_EVALS = "tool_call_evals"
SAFETY_EVALS = "safety_evals"

BUILTIN_CATEGORIES = {
    PROVIDER_EVALS,
    STREAMING_EVALS,
    CONTEXT_EVALS,
    RETRIEVAL_EVALS,
    AGENT_RUN_EVALS,
    TOOL_CALL_EVALS,
    SAFETY_EVALS,
}
CATEGORY_ALIASES = {
    "providers": PROVIDER_EVALS,
    "provider": PROVIDER_EVALS,
    "provider_evals": PROVIDER_EVALS,
    "streaming": STREAMING_EVALS,
    "streaming_evals": STREAMING_EVALS,
    "context": CONTEXT_EVALS,
    "context_evals": CONTEXT_EVALS,
    "retrieval": RETRIEVAL_EVALS,
    "retrieval_evals": RETRIEVAL_EVALS,
    "agents": AGENT_RUN_EVALS,
    "agent": AGENT_RUN_EVALS,
    "agent_run_evals": AGENT_RUN_EVALS,
    "tools": TOOL_CALL_EVALS,
    "tool": TOOL_CALL_EVALS,
    "tool_call_evals": TOOL_CALL_EVALS,
    "safety": SAFETY_EVALS,
    "safety_evals": SAFETY_EVALS,
}


@dataclass(frozen=True)
class EvalContext:
    root: Path
    workspace: Path


@dataclass(frozen=True)
class EvalCase:
    name: str
    category: str
    description: str
    run: Callable[[EvalContext], str]


def normalize_category(category: str | None) -> str | None:
    if category is None:
        return None
    normalized = category.strip().lower()
    try:
        return CATEGORY_ALIASES[normalized]
    except KeyError as error:
        aliases = ", ".join(sorted(CATEGORY_ALIASES))
        raise ValueError(
            f"Unknown eval category: {category}. Known categories: {aliases}"
        ) from error


def builtin_cases() -> list[EvalCase]:
    return [
        EvalCase(
            "local_stub_non_streaming",
            PROVIDER_EVALS,
            "local-stub non-streaming",
            _provider_local_stub_non_streaming,
        ),
        EvalCase(
            "local_stub_streaming",
            PROVIDER_EVALS,
            "local-stub streaming",
            _provider_local_stub_streaming,
        ),
        EvalCase(
            "missing_api_key_warning",
            PROVIDER_EVALS,
            "missing API key warning",
            _provider_missing_api_key_warning,
        ),
        EvalCase(
            "provider_factory_selects_adapter",
            PROVIDER_EVALS,
            "provider factory selects adapter",
            _provider_factory_selects_adapter,
        ),
        EvalCase(
            "streamed_chunks_reconstruct_final_message",
            STREAMING_EVALS,
            "stream chunks reconstruct final",
            _streamed_chunks_reconstruct_final_message,
        ),
        EvalCase(
            "usage_tracked_after_stream",
            STREAMING_EVALS,
            "usage tracked after stream",
            _usage_tracked_after_stream,
        ),
        EvalCase(
            "fallback_to_non_streaming_when_unsupported",
            STREAMING_EVALS,
            "stream fallback",
            _fallback_to_non_streaming_when_unsupported,
        ),
        EvalCase(
            "context_percentage_statuses",
            CONTEXT_EVALS,
            "context percentage ok/warn/critical",
            _context_percentage_statuses,
        ),
        EvalCase(
            "compaction_removes_oldest_messages",
            CONTEXT_EVALS,
            "compaction removes oldest",
            _compaction_removes_oldest_messages,
        ),
        EvalCase(
            "no_hidden_files_or_local_data_sent_by_default",
            CONTEXT_EVALS,
            "no hidden local data by default",
            _no_hidden_files_or_local_data_sent_by_default,
        ),
        EvalCase(
            "default_retrieval_off",
            RETRIEVAL_EVALS,
            "default retrieval off",
            _default_retrieval_off,
        ),
        EvalCase("memory_opt_in_works", RETRIEVAL_EVALS, "memory opt-in", _memory_opt_in_works),
        EvalCase("brain_opt_in_works", RETRIEVAL_EVALS, "brain opt-in", _brain_opt_in_works),
        EvalCase(
            "dry_run_context_does_not_call_model",
            RETRIEVAL_EVALS,
            "dry-run context no model",
            _dry_run_context_does_not_call_model,
        ),
        EvalCase(
            "retrieved_context_limited_to_configured_max_results",
            RETRIEVAL_EVALS,
            "retrieval max results",
            _retrieved_context_limited_to_configured_max_results,
        ),
        EvalCase(
            "text_only_agent_run",
            AGENT_RUN_EVALS,
            "text-only local-stub agent",
            _text_only_agent_run,
        ),
        EvalCase(
            "tool_enabled_agent_run_with_local_stub",
            AGENT_RUN_EVALS,
            "tool-enabled local-stub agent",
            _tool_enabled_agent_run_with_local_stub,
        ),
        EvalCase("max_steps_enforced", AGENT_RUN_EVALS, "max steps enforced", _max_steps_enforced),
        EvalCase(
            "unknown_tool_blocked",
            AGENT_RUN_EVALS,
            "unknown tool blocked",
            _agent_unknown_tool_blocked,
        ),
        EvalCase(
            "policy_violation_blocks_tool_call",
            AGENT_RUN_EVALS,
            "policy blocks tool call",
            _agent_policy_violation_blocks_tool_call,
        ),
        EvalCase(
            "unknown_tool_blocked", TOOL_CALL_EVALS, "unknown tool blocked", _unknown_tool_blocked
        ),
        EvalCase(
            "policy_violation_blocks_tool_call",
            TOOL_CALL_EVALS,
            "policy blocks tool call",
            _policy_violation_blocks_tool_call,
        ),
        EvalCase(
            "tool_registry_has_no_shell_execution",
            TOOL_CALL_EVALS,
            "no shell execution tool",
            _no_shell_execution_tool_exposed,
        ),
        EvalCase("no_env_read", SAFETY_EVALS, "no .env read", _no_env_read),
        EvalCase("no_api_key_printed", SAFETY_EVALS, "no API key printed", _no_api_key_printed),
        EvalCase(
            "no_shell_execution_tool_exposed",
            SAFETY_EVALS,
            "no shell execution tool",
            _no_shell_execution_tool_exposed,
        ),
        EvalCase(
            "destructive_command_blocked",
            SAFETY_EVALS,
            "destructive command blocked",
            _destructive_command_blocked,
        ),
    ]


def _local_provider() -> ModelProvider:
    return ModelProvider(name="local", kind="local_stub", supports_streaming=True)


def _local_profile() -> ModelProfile:
    return ModelProfile(
        name="local-stub",
        provider="local",
        model="local-stub",
        effort="low",
        context_window_tokens=10_000,
        input_token_cost_per_1m=0.0,
        output_token_cost_per_1m=0.0,
        default_temperature=0.0,
    )


def _provider_local_stub_non_streaming(_context: EvalContext) -> str:
    response = LocalStubProvider().chat(
        ChatRequest(message="eval ping"), _local_provider(), _local_profile()
    )
    assert_equal(response.status, "ok", "local-stub response should be ok.")
    assert_in("eval ping", response.text, "local-stub response should echo the prompt.")
    assert_true(response.usage.total_tokens > 0, "local-stub should report deterministic usage.")
    return "local-stub non-streaming returned deterministic text and usage."


def _provider_local_stub_streaming(_context: EvalContext) -> str:
    request = ChatRequest(message="stream ping")
    events = list(LocalStubProvider().stream_chat(request, _local_provider(), _local_profile()))
    text = "".join(event.delta for event in events if event.type == "content_delta")
    usage = next(event.usage for event in events if event.type == "usage_delta")
    assert_in("stream ping", text, "streamed local-stub chunks should reconstruct the prompt.")
    assert_true(usage is not None and usage.total_tokens > 0, "stream should include usage.")
    return "local-stub streaming emitted content chunks and usage."


def _provider_missing_api_key_warning(_context: EvalContext) -> str:
    env_name = "AGENTOS_EVAL_MISSING_OPENAI_KEY"
    previous = os.environ.pop(env_name, None)
    try:
        provider = ModelProvider(
            name="openai-eval",
            kind="openai",
            base_url="https://api.openai.com/v1",
            api_key_env=env_name,
        )
        warning = provider_adapter(provider).validate_config(provider, _openai_profile())
    finally:
        if previous is not None:
            os.environ[env_name] = previous
    assert_true(warning is not None, "OpenAI provider should warn when API key env is unset.")
    assert_in(env_name, warning, "Warning should name the missing environment variable.")
    assert_in("does not read .env", warning, "Warning should make .env behavior clear.")
    return "missing OpenAI API key produced a clear local warning without network access."


def _provider_factory_selects_adapter(_context: EvalContext) -> str:
    adapter = provider_adapter(_local_provider())
    assert_true(
        isinstance(adapter, LocalStubProvider), "Provider factory should select LocalStubProvider."
    )
    return "provider factory selected the local-stub adapter."


def _openai_profile() -> ModelProfile:
    return ModelProfile(
        name="openai-eval-profile",
        provider="openai-eval",
        model="gpt-eval",
        effort="low",
        context_window_tokens=128_000,
    )


def _streamed_chunks_reconstruct_final_message(context: EvalContext) -> str:
    chunks: list[str] = []
    response = chat_once(
        context.workspace, message="stream reconstruct", stream=True, on_delta=chunks.append
    )
    assert_equal("".join(chunks), response.text, "Streamed chunks should match final text.")
    assert_true(response.streamed, "Response should be marked streamed.")
    return "streamed chunks matched the final response text."


def _usage_tracked_after_stream(context: EvalContext) -> str:
    response = chat_once(context.workspace, message="stream usage", stream=True)
    status = inspect_model_status(context.workspace)
    assert_true(response.usage.total_tokens > 0, "Streamed response should include usage.")
    assert_true(
        status.usage.cumulative_total_tokens >= response.usage.total_tokens,
        "Usage should be persisted after stream.",
    )
    return "streaming usage was persisted locally after completion."


def _fallback_to_non_streaming_when_unsupported(context: EvalContext) -> str:
    root = context.workspace
    provider = ModelProvider(name="local", kind="local_stub", supports_streaming=False)
    profile = _local_profile()
    write_model_config(root / ".agentos" / "models.yaml", _model_config(provider, profile))
    response = chat_once(root, message="fallback", stream=True)
    assert_true(
        response.stream_fallback, "Unsupported streaming should fall back to non-streaming."
    )
    assert_true(not response.streamed, "Fallback response should not be marked streamed.")
    return "provider-level streaming opt-out fell back to non-streaming."


def _model_config(provider: ModelProvider, profile: ModelProfile) -> ModelConfig:
    return ModelConfig(
        active=ActiveModelState(
            active_model_profile=profile.name,
            active_provider=provider.name,
            active_model=profile.model,
            effort=profile.effort,
            context_window_tokens=profile.context_window_tokens,
            cumulative_estimated_cost_usd=0.0,
        ),
        providers=[provider],
        model_profiles=[profile],
    )


def _context_percentage_statuses(_context: EvalContext) -> str:
    ok = estimate_context_usage(
        model_profile="eval", context_window_tokens=100, reported_input_tokens=79
    )
    warn = estimate_context_usage(
        model_profile="eval", context_window_tokens=100, reported_input_tokens=80
    )
    critical = estimate_context_usage(
        model_profile="eval", context_window_tokens=100, reported_input_tokens=95
    )
    assert_equal(ok.status, "ok", "79% should be ok.")
    assert_equal(warn.status, "warn", "80% should warn.")
    assert_equal(critical.status, "critical", "95% should be critical.")
    return "context usage thresholds returned ok, warn, and critical."


def _compaction_removes_oldest_messages(_context: EvalContext) -> str:
    messages = [
        {"role": "user", "content": "oldest " + "x" * 120},
        {"role": "assistant", "content": "middle " + "y" * 120},
        {"role": "user", "content": "newest"},
    ]
    result = compact_session_history(
        messages,
        model_profile="eval",
        context_window_tokens=60,
        max_used_percent=80,
    )
    assert_true(result.dropped_count > 0, "Compaction should drop at least one old message.")
    assert_not_in(
        "oldest",
        [message.content for message in result.messages],
        "Oldest message should be dropped.",
    )
    assert_equal(result.messages[-1].content, "newest", "Newest message should be retained.")
    return "compaction dropped oldest messages and retained the newest message."


def _no_hidden_files_or_local_data_sent_by_default(context: EvalContext) -> str:
    hidden = context.workspace / ".hidden-note"
    hidden.write_text("SHOULD_NOT_BE_SENT", encoding="utf-8")
    response = chat_once(context.workspace, message="default context check")
    assert_not_in(
        "SHOULD_NOT_BE_SENT", response.text, "Default chat should not include hidden local data."
    )
    assert_in("default context check", response.text, "Default prompt should still be sent.")
    return "default model call did not include hidden local data."


def _default_retrieval_off(context: EvalContext) -> str:
    MemoryStore(context.workspace).add_memory(
        "default", "Eval memory", "note", "retrieval secret", []
    )
    response = chat_once(context.workspace, message="hello")
    assert_not_in("retrieval secret", response.text, "Retrieval should be off by default.")
    return "chat did not include memory context without opt-in."


def _memory_opt_in_works(context: EvalContext) -> str:
    MemoryStore(context.workspace).add_memory(
        "default", "Eval memory", "note", "memory optin phrase", []
    )
    retrieval = build_retrieval_context(
        context.workspace,
        "memory optin",
        RetrievalSettings(with_memory=True, memory_limit=5),
    )
    assert_true(retrieval.has_context, "Memory opt-in should retrieve local memory.")
    assert_in(
        "memory optin phrase", retrieval.block, "Memory context should include matching excerpt."
    )
    return "memory retrieval opt-in returned the matching local memory."


def _brain_opt_in_works(context: EvalContext) -> str:
    note = context.workspace / "strategy.md"
    note.write_text("# Eval Strategy\n\nbrain optin phrase", encoding="utf-8")
    store = StrategicBrainStore(context.workspace)
    store.ingest_document(note)
    with sqlite3.connect(context.workspace / ".agentos" / "brain" / "index.db") as connection:
        connection.execute("UPDATE documents SET path = ?", ("strategy.md",))
        try:
            connection.execute("UPDATE chunks_fts SET path = ?", ("strategy.md",))
        except sqlite3.OperationalError:
            pass
    retrieval = build_retrieval_context(
        context.workspace,
        "brain optin",
        RetrievalSettings(with_brain=True, brain_limit=5),
    )
    assert_true(retrieval.has_context, "Brain opt-in should retrieve indexed document.")
    assert_in(
        "brain optin phrase", retrieval.block, "Brain context should include matching excerpt."
    )
    return "Strategic Brain opt-in returned the matching local document."


def _dry_run_context_does_not_call_model(context: EvalContext) -> str:
    MemoryStore(context.workspace).add_memory(
        "default", "Dry run", "note", "dry run context only", []
    )
    retrieval = build_retrieval_context(
        context.workspace,
        "dry run",
        RetrievalSettings(with_memory=True),
    )
    usage_db = context.workspace / ".agentos" / "usage" / "usage.db"
    assert_true(retrieval.has_context, "Dry-run context should build retrieval context.")
    assert_true(not usage_db.exists(), "Building dry-run context should not record model usage.")
    return "dry-run context built local context without creating model usage."


def _retrieved_context_limited_to_configured_max_results(context: EvalContext) -> str:
    store = MemoryStore(context.workspace)
    for index in range(5):
        store.add_memory("default", f"Limited {index}", "note", "limited result phrase", [])
    retrieval = build_retrieval_context(
        context.workspace,
        "limited result",
        RetrievalSettings(with_memory=True, memory_limit=2),
    )
    assert_equal(len(retrieval.memory_items), 2, "Memory retrieval should respect max results.")
    return "retrieved memory context was limited to the configured result count."


def _text_only_agent_run(context: EvalContext) -> str:
    plan = AgentPlanner(context.workspace).next_step(
        task="answer without tools",
        role="assistant",
        tools=[],
        previous_results=[],
        step=1,
    )
    assert_equal(plan.tool_calls, [], "Text-only local-stub plan should not request tools.")
    assert_equal(
        plan.final_answer,
        "local-stub final answer without tools.",
        "Text-only plan should produce final answer.",
    )
    return "local-stub planner returned a text-only final answer without tools."


def _tool_enabled_agent_run_with_local_stub(context: EvalContext) -> str:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="fake_tool",
            description="Fake safe eval tool.",
            input_schema={"type": "object", "properties": {}, "required": []},
            output_schema={"type": "object", "properties": {}},
        ),
        lambda _root, args: {"called": True, "query": args.get("query", "")},
    )
    result = AgentToolLoop(context.workspace, registry=registry).run(
        name="Eval Agent",
        role="testing",
        task="use fake tool",
        max_steps=3,
    )
    assert_equal(result.status, "completed", "Tool-enabled agent should complete.")
    assert_equal(result.tool_results[0].status, "ok", "Fake tool should execute successfully.")
    return "tool-enabled local-stub agent executed a safe local tool."


def _max_steps_enforced(context: EvalContext) -> str:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="fake_tool",
            description="Fake safe eval tool.",
            input_schema={"type": "object", "properties": {}, "required": []},
            output_schema={"type": "object", "properties": {}},
        ),
        lambda _root, _args: {"called": True},
    )
    result = AgentToolLoop(context.workspace, registry=registry).run(
        name="Eval Agent",
        role="testing",
        task="use fake tool repeatedly",
        max_steps=1,
    )
    assert_equal(
        result.final_answer, "Stopped after max steps.", "Agent loop should enforce max steps."
    )
    assert_equal(len(result.tool_results), 1, "Agent should stop after one tool call.")
    return "agent loop stopped at the configured max step count."


class _SingleToolPlanner:
    def __init__(self, call: ToolCall) -> None:
        self.call = call

    def next_step(
        self,
        *,
        task: str,
        role: str,
        tools: list[str],
        previous_results: list[ToolResult],
        step: int,
    ) -> ToolProtocolMessage:
        if previous_results or step > 1:
            return ToolProtocolMessage(tool_calls=[], final_answer="local-stub final answer.")
        return ToolProtocolMessage(tool_calls=[self.call])


def _agent_unknown_tool_blocked(context: EvalContext) -> str:
    result = AgentToolLoop(
        context.workspace,
        planner=_SingleToolPlanner(ToolCall(name="shell", arguments={"command": "echo unsafe"})),
    ).run(
        name="Eval Agent",
        role="testing",
        task="request unknown shell tool",
        max_steps=2,
    )
    assert_equal(result.status, "completed", "Agent loop should complete after a blocked tool.")
    assert_equal(result.tool_results[0].status, "blocked", "Unknown shell tool should be blocked.")
    assert_in(
        "Unknown tool",
        result.tool_results[0].error or "",
        "Blocked result should explain unknown tool.",
    )
    return "agent loop routed an unknown tool request through the executor and blocked it."


def _agent_policy_violation_blocks_tool_call(context: EvalContext) -> str:
    result = AgentToolLoop(
        context.workspace,
        planner=_SingleToolPlanner(
            ToolCall(name="memory_search", arguments={"query": "rm -rf project"})
        ),
    ).run(
        name="Eval Agent",
        role="testing",
        task="request policy-violating memory search",
        max_steps=2,
    )
    assert_equal(result.status, "completed", "Agent loop should complete after a blocked tool.")
    assert_equal(
        result.tool_results[0].status,
        "blocked",
        "Policy-violating agent tool arguments should be blocked.",
    )
    assert_in(
        "destructive",
        result.tool_results[0].error or "",
        "Blocked tool call should mention destructive command.",
    )
    return (
        "agent loop routed policy-violating tool arguments through the executor and blocked them."
    )


def _unknown_tool_blocked(context: EvalContext) -> str:
    result = ToolExecutor(context.workspace, create_builtin_tool_registry()).execute(
        ToolCall(name="shell", arguments={"command": "echo unsafe"})
    )
    assert_equal(result.status, "blocked", "Unknown shell tool should be blocked.")
    assert_in("Unknown tool", result.error or "", "Blocked result should explain unknown tool.")
    return "unknown tool request was blocked before execution."


def _policy_violation_blocks_tool_call(context: EvalContext) -> str:
    result = ToolExecutor(context.workspace, create_builtin_tool_registry()).execute(
        ToolCall(name="memory_search", arguments={"query": "rm -rf project"})
    )
    assert_equal(result.status, "blocked", "Policy-violating tool arguments should be blocked.")
    assert_in(
        "destructive", result.error or "", "Blocked tool call should mention destructive command."
    )
    return "policy checker blocked destructive text before tool execution."


def _no_env_read(context: EvalContext) -> str:
    env_path = context.workspace / ".env"
    env_path.write_text("AGENTOS_EVAL_SHOULD_NOT_BE_READ=1", encoding="utf-8")
    create_default_policies(context.workspace)
    result = PolicyChecker.from_directory(context.workspace / "policies").check_path(".env")
    assert_true(not result.allowed, ".env should be blocked before access.")
    return ".env path was blocked by policy without opening the file."


def _no_api_key_printed(context: EvalContext) -> str:
    secret = "agentos-eval-secret-value"
    env_name = "AGENTOS_EVAL_PRESENT_KEY"
    previous = os.environ.get(env_name)
    os.environ[env_name] = secret
    try:
        provider = ModelProvider(name="openai-eval", kind="openai", api_key_env=env_name)
        profile = _openai_profile().model_copy(update={"provider": provider.name})
        write_model_config(
            context.workspace / ".agentos" / "models.yaml", _model_config(provider, profile)
        )
        status = inspect_model_status(context.workspace)
    finally:
        if previous is None:
            os.environ.pop(env_name, None)
        else:
            os.environ[env_name] = previous
    rendered = status.model_dump_json()
    assert_not_in(secret, rendered, "Provider status must not print API key values.")
    assert_in(env_name, rendered, "Provider status may print safe env var names.")
    return "provider status omitted API key values and showed only env var metadata."


def _no_shell_execution_tool_exposed(_context: EvalContext) -> str:
    names = {tool.name for tool in create_builtin_tool_registry().list_tools()}
    for blocked_name in {"shell", "command_exec", "file_read", "file_write"}:
        assert_not_in(
            blocked_name, names, f"{blocked_name} must not be exposed as a built-in tool."
        )
    return "built-in tool registry exposes no shell or arbitrary file tools."


def _destructive_command_blocked(context: EvalContext) -> str:
    create_default_policies(context.workspace)
    result = PolicyChecker.from_directory(context.workspace / "policies").check_command(
        "rm -rf project"
    )
    assert_true(not result.allowed, "Destructive command should be blocked.")
    assert_equal(
        result.rule_type,
        "destructive_command",
        "Destructive command should match destructive rule.",
    )
    return "policy checker blocked a destructive command string."
