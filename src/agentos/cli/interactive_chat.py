from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

from agentos import __version__
from agentos.agents.registry import AgentRuntimeRegistry
from agentos.context.compactor import compact_session_history
from agentos.context.estimator import estimate_context_usage, estimate_tokens
from agentos.context.schemas import ContextUsage
from agentos.logging.traces import TraceEventType, TraceLogger
from agentos.memory.store import MemoryStore
from agentos.models.client import chat_once
from agentos.models.config import (
    inspect_model_status,
    load_model_config,
    reset_usage,
    set_active_model_profile,
)
from agentos.models.pricing import format_estimated_cost
from agentos.retrieval.context_builder import build_retrieval_context
from agentos.retrieval.schemas import RetrievalContext, RetrievalSettings

DEFAULT_SYSTEM_PROMPT = (
    "You are AgentOS Personal interactive chat. Answer the user's explicit "
    "messages. Retrieval-augmented chat is a future feature, so do not assume "
    "access to local memory, brain documents, traces, or files."
)


class ParsedInteractiveCommand(BaseModel):
    name: str
    args: list[str] = []
    raw: str = ""


class ChatHistoryMessage(BaseModel):
    role: str
    content: str


@dataclass(frozen=True)
class InteractiveTurnResult:
    output: str
    should_exit: bool = False
    dashboard_requested: bool = False


def parse_interactive_command(line: str) -> ParsedInteractiveCommand:
    stripped = line.strip()
    lowered = stripped.lower()
    if lowered in {"help", "exit", "quit", "version", "doctor"}:
        return ParsedInteractiveCommand(name=lowered, raw=line)
    if not stripped.startswith("/"):
        return ParsedInteractiveCommand(name="message", args=[line], raw=line)

    parts = stripped.split()
    command = parts[0].lower()
    args = parts[1:]
    if command == "/model":
        if not args:
            return ParsedInteractiveCommand(name="model", raw=line)
        if args[0] == "list":
            return ParsedInteractiveCommand(name="model.list", args=args[1:], raw=line)
        if args[0] == "set":
            return ParsedInteractiveCommand(name="model.set", args=args[1:], raw=line)
    if command == "/effort":
        return ParsedInteractiveCommand(name="effort", args=args, raw=line)
    if command == "/stream":
        if args[:1] == ["on"]:
            return ParsedInteractiveCommand(name="stream.on", args=args[1:], raw=line)
        if args[:1] == ["off"]:
            return ParsedInteractiveCommand(name="stream.off", args=args[1:], raw=line)
        if args[:1] == ["status"]:
            return ParsedInteractiveCommand(name="stream.status", args=args[1:], raw=line)
        return ParsedInteractiveCommand(name="stream.status", args=args, raw=line)
    if command == "/usage":
        if args and args[0] == "reset":
            return ParsedInteractiveCommand(name="usage.reset", args=args[1:], raw=line)
        return ParsedInteractiveCommand(name="usage", args=args, raw=line)
    if command == "/agents":
        return ParsedInteractiveCommand(name="agents", args=args, raw=line)
    if command == "/clear":
        return ParsedInteractiveCommand(name="clear", raw=line)
    if command == "/dashboard":
        return ParsedInteractiveCommand(name="dashboard", raw=line)
    if command == "/memory" and args[:1] == ["search"]:
        return ParsedInteractiveCommand(name="memory.search", args=args[1:], raw=line)
    if command == "/memory" and args[:1] == ["on"]:
        return ParsedInteractiveCommand(name="memory.on", raw=line)
    if command == "/memory" and args[:1] == ["off"]:
        return ParsedInteractiveCommand(name="memory.off", raw=line)
    if command == "/brain" and args[:1] == ["on"]:
        return ParsedInteractiveCommand(name="brain.on", raw=line)
    if command == "/brain" and args[:1] == ["off"]:
        return ParsedInteractiveCommand(name="brain.off", raw=line)
    if command == "/context":
        if args[:1] == ["show"]:
            return ParsedInteractiveCommand(name="context.show", raw=line)
        if args[:1] == ["clear"]:
            return ParsedInteractiveCommand(name="context.clear", raw=line)
        if args[:1] == ["status"]:
            return ParsedInteractiveCommand(name="context.status", raw=line)
    if command == "/retrieve" and args[:1] == ["memory"]:
        return ParsedInteractiveCommand(name="retrieve.memory", args=args[1:], raw=line)
    if command == "/retrieve" and args[:1] == ["brain"]:
        return ParsedInteractiveCommand(name="retrieve.brain", args=args[1:], raw=line)
    return ParsedInteractiveCommand(name="unknown", args=args, raw=line)


class InteractiveChatSession:
    def __init__(
        self,
        root: Path,
        *,
        max_history_messages: int = 20,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        stream_writer: Callable[[str], None] | None = None,
    ) -> None:
        self.root = root
        self.max_history_messages = max(0, max_history_messages)
        self.system_prompt = system_prompt
        self.history: list[ChatHistoryMessage] = []
        self.effort_override: str | None = None
        self.stream_enabled = True
        self.stream_writer = stream_writer
        self.memory_retrieval_enabled = False
        self.brain_retrieval_enabled = False
        self.memory_query: str | None = None
        self.brain_query: str | None = None
        self.last_retrieval_context: RetrievalContext | None = None
        self.session_id = uuid4().hex
        self.trace = TraceLogger(root)

    def handle_input(self, line: str) -> InteractiveTurnResult:
        parsed = parse_interactive_command(line)
        if parsed.name == "message":
            return self._handle_message(line)
        if parsed.name in {"exit", "quit"}:
            return InteractiveTurnResult("Goodbye.", should_exit=True)
        if parsed.name == "help":
            return InteractiveTurnResult(_help_text())
        if parsed.name == "version":
            return InteractiveTurnResult(f"AgentOS Personal {__version__}")
        if parsed.name == "doctor":
            return InteractiveTurnResult(
                f"Run `agentos doctor --root {self.root}` for the full diagnostic report."
            )
        if parsed.name == "model":
            return InteractiveTurnResult(self._model_status())
        if parsed.name == "model.list":
            return InteractiveTurnResult(self._model_list())
        if parsed.name == "model.set":
            return InteractiveTurnResult(self._model_set(parsed.args))
        if parsed.name == "effort":
            return InteractiveTurnResult(self._effort(parsed.args))
        if parsed.name == "stream.on":
            self.stream_enabled = True
            return InteractiveTurnResult("Streaming enabled.")
        if parsed.name == "stream.off":
            self.stream_enabled = False
            return InteractiveTurnResult("Streaming disabled.")
        if parsed.name == "stream.status":
            return InteractiveTurnResult(self._stream_status())
        if parsed.name == "usage":
            return InteractiveTurnResult(self._usage())
        if parsed.name == "usage.reset":
            return InteractiveTurnResult(self._usage_reset(parsed.args))
        if parsed.name == "agents":
            return InteractiveTurnResult(self._agents())
        if parsed.name == "clear":
            self.history.clear()
            return InteractiveTurnResult("Session history cleared.")
        if parsed.name == "dashboard":
            return InteractiveTurnResult("Dashboard refreshed.", dashboard_requested=True)
        if parsed.name == "memory.search":
            return InteractiveTurnResult(self._memory_search(parsed.args))
        if parsed.name == "memory.on":
            self.memory_retrieval_enabled = True
            return InteractiveTurnResult("Memory retrieval enabled for this session.")
        if parsed.name == "memory.off":
            self.memory_retrieval_enabled = False
            self.memory_query = None
            return InteractiveTurnResult("Memory retrieval disabled for this session.")
        if parsed.name == "brain.on":
            self.brain_retrieval_enabled = True
            return InteractiveTurnResult("Brain retrieval enabled for this session.")
        if parsed.name == "brain.off":
            self.brain_retrieval_enabled = False
            self.brain_query = None
            return InteractiveTurnResult("Brain retrieval disabled for this session.")
        if parsed.name == "context.status":
            return InteractiveTurnResult(self._context_status())
        if parsed.name == "context.show":
            block = (
                self.last_retrieval_context.block
                if self.last_retrieval_context
                else "No context built."
            )
            return InteractiveTurnResult(block)
        if parsed.name == "context.clear":
            self.last_retrieval_context = None
            self.memory_query = None
            self.brain_query = None
            return InteractiveTurnResult("Retrieval context cleared.")
        if parsed.name == "retrieve.memory":
            query = " ".join(parsed.args).strip()
            self.memory_retrieval_enabled = True
            self.memory_query = query or None
            return InteractiveTurnResult(
                f"Memory retrieval query set: {self.memory_query or 'latest message'}"
            )
        if parsed.name == "retrieve.brain":
            query = " ".join(parsed.args).strip()
            self.brain_retrieval_enabled = True
            self.brain_query = query or None
            return InteractiveTurnResult(
                f"Brain retrieval query set: {self.brain_query or 'latest message'}"
            )
        return InteractiveTurnResult(f"Unknown interactive command: {line}")

    def _handle_message(self, message: str) -> InteractiveTurnResult:
        notices = self._prepare_context(message)
        status = inspect_model_status(self.root)
        prompt = self._render_prompt(message)
        input_estimate = estimate_tokens(self.system_prompt, prompt)
        self.trace.log_event(
            TraceEventType.INTERACTIVE_MESSAGE_SENT,
            command="interactive.chat",
            status="sent",
            payload={
                "model_profile": status.active_model_profile,
                "input_estimate_tokens": input_estimate,
                "history_messages": len(self.history),
            },
        )
        response = chat_once(
            self.root,
            message=prompt,
            effort=self.effort_override,
            system_prompt=self.system_prompt,
            session_id=self.session_id,
            stream=self.stream_enabled,
            on_delta=self.stream_writer,
            retrieval_settings=self._retrieval_settings(),
        )
        if self.memory_retrieval_enabled or self.brain_retrieval_enabled:
            self.last_retrieval_context = build_retrieval_context(
                self.root,
                prompt,
                self._retrieval_settings(),
            )
        if response.status != "ok":
            return InteractiveTurnResult("\n".join([*notices, response.text]).strip())

        self.history.append(ChatHistoryMessage(role="user", content=message))
        self.history.append(ChatHistoryMessage(role="assistant", content=response.text))
        notices.extend(self._enforce_history_limit())
        context_notice = self._post_response_context_notice()
        if context_notice:
            notices.append(context_notice)
        self.trace.log_event(
            TraceEventType.INTERACTIVE_MESSAGE_RECEIVED,
            command="interactive.chat",
            status="received",
            payload={
                "model_profile": response.model_profile,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "history_messages": len(self.history),
            },
        )
        if response.streamed and not response.stream_fallback and self.stream_writer:
            return InteractiveTurnResult("\n".join(notices).strip())
        return InteractiveTurnResult("\n".join([*notices, response.text]).strip())

    def _prepare_context(self, latest_message: str) -> list[str]:
        notices = self._enforce_history_limit()
        active = load_model_config(self.root).active
        compaction = compact_session_history(
            self.history,
            model_profile=active.active_model_profile,
            context_window_tokens=active.context_window_tokens,
            system_prompt=self.system_prompt,
            latest_message=latest_message,
            max_used_percent=95.0,
        )
        if compaction.dropped_count:
            self.history = [
                ChatHistoryMessage(role=message.role, content=message.content)
                for message in compaction.messages
            ]
            notice = compaction.notice or (
                f"Context compacted: dropped {compaction.dropped_count} oldest message(s)."
            )
            self.trace.log_event(
                TraceEventType.CONTEXT_COMPACTED,
                command="interactive.chat",
                status="compacted",
                payload={
                    "dropped_messages": compaction.dropped_count,
                    "context_percent": _rounded_percent(compaction.usage),
                },
            )
            notices.append(notice)
        if _needs_context_warning(compaction.usage):
            percent = compaction.usage.used_percent or 0.0
            notice = f"Context usage warning: {percent:.2f}% of active model window."
            self.trace.log_event(
                TraceEventType.CONTEXT_WARNING,
                command="interactive.chat",
                status=compaction.usage.status,
                payload={"context_percent": round(percent, 2)},
            )
            notices.append(notice)
        return notices

    def _post_response_context_notice(self) -> str | None:
        usage = self._context_usage()
        if not _needs_context_warning(usage):
            return None
        percent = usage.used_percent or 0.0
        self.trace.log_event(
            TraceEventType.CONTEXT_WARNING,
            command="interactive.chat",
            status=usage.status,
            payload={"context_percent": round(percent, 2), "phase": "post_response"},
        )
        return f"Context usage warning: {percent:.2f}% of active model window."

    def _enforce_history_limit(self) -> list[str]:
        if self.max_history_messages <= 0:
            dropped = len(self.history)
            self.history.clear()
        else:
            dropped = max(0, len(self.history) - self.max_history_messages)
            if dropped:
                del self.history[:dropped]
        if not dropped:
            return []
        self.trace.log_event(
            TraceEventType.CONTEXT_COMPACTED,
            command="interactive.chat",
            status="compacted",
            payload={"dropped_messages": dropped, "reason": "max_history_messages"},
        )
        return [f"Context compacted: dropped {dropped} oldest message(s)."]

    def _estimated_context_percent(self, latest: str | None = None) -> float:
        return self._context_usage(latest).used_percent or 0.0

    def _context_usage(self, latest: str | None = None) -> ContextUsage:
        active = load_model_config(self.root).active
        return estimate_context_usage(
            model_profile=active.active_model_profile,
            context_window_tokens=active.context_window_tokens,
            input_texts=[
                self.system_prompt,
                *(message.content for message in self.history),
                latest or "",
            ],
        )

    def _render_prompt(self, latest_message: str) -> str:
        if not self.history:
            return latest_message
        lines = [
            "Conversation history for this session only:",
            *[f"{message.role}: {message.content}" for message in self.history],
            "Latest user message:",
            latest_message,
        ]
        return "\n".join(lines)

    def _model_status(self) -> str:
        status = inspect_model_status(self.root)
        return (
            f"model={status.active_model_profile} provider={status.active_provider} "
            f"status={status.status} effort={status.usage.effort}"
        )

    def _stream_status(self) -> str:
        status = inspect_model_status(self.root)
        config = load_model_config(self.root)
        provider = next(
            provider for provider in config.providers if provider.name == status.active_provider
        )
        supported = provider.supports_streaming or provider.kind in {
            "local_stub",
            "openai",
            "openai_compatible",
        }
        enabled = "on" if self.stream_enabled else "off"
        support = "supported" if supported else "not supported"
        return f"stream={enabled} provider={status.active_provider} {support}"

    def _retrieval_settings(self) -> RetrievalSettings:
        return RetrievalSettings(
            with_memory=self.memory_retrieval_enabled,
            with_brain=self.brain_retrieval_enabled,
            memory_query=self.memory_query,
            brain_query=self.brain_query,
        )

    def _context_status(self) -> str:
        return (
            f"memory={'on' if self.memory_retrieval_enabled else 'off'} "
            f"brain={'on' if self.brain_retrieval_enabled else 'off'} "
            f"context={'built' if self.last_retrieval_context else 'empty'}"
        )

    def _model_list(self) -> str:
        config = load_model_config(self.root)
        lines = []
        for profile in config.model_profiles:
            active = "*" if profile.name == config.active.active_model_profile else " "
            lines.append(
                f"{active} {profile.name} provider={profile.provider} "
                f"model={profile.model} effort={profile.effort} enabled={profile.enabled}"
            )
        return "\n".join(lines)

    def _model_set(self, args: list[str]) -> str:
        if not args:
            return "Usage: /model set <profile>"
        config = set_active_model_profile(self.root, args[0])
        self.effort_override = config.active.effort
        return f"Active model profile set to {config.active.active_model_profile}"

    def _effort(self, args: list[str]) -> str:
        if not args or args[0] not in {"low", "medium", "high", "max"}:
            return "Usage: /effort low|medium|high|max"
        self.effort_override = args[0]
        return f"Session effort set to {args[0]}"

    def _usage(self) -> str:
        active = load_model_config(self.root).active
        return "\n".join(
            [
                f"active_model_profile: {active.active_model_profile}",
                f"context_used_tokens: {active.context_used_tokens}",
                f"context_used_percent: {active.context_used_percent:.2f}%",
                f"cumulative_input_tokens: {active.cumulative_input_tokens}",
                f"cumulative_output_tokens: {active.cumulative_output_tokens}",
                f"cumulative_total_tokens: {active.cumulative_total_tokens}",
                "cumulative_estimated_cost_usd: "
                f"{format_estimated_cost(active.cumulative_estimated_cost_usd)}",
            ]
        )

    def _usage_reset(self, args: list[str]) -> str:
        if "--confirm" not in args:
            return "Usage reset requires --confirm."
        reset_usage(self.root, confirm=True)
        return "Usage reset"

    def _agents(self) -> str:
        agents = AgentRuntimeRegistry(self.root).list_agents()
        if not agents:
            return "No agents in runtime registry."
        return "\n".join(
            (
                f"{agent.id} {agent.name} {agent.kind.value} {agent.status.value} "
                f"role={agent.role} model={agent.model_profile} effort={agent.effort} "
                f"task={agent.current_task}"
            )
            for agent in agents
        )

    def _memory_search(self, args: list[str]) -> str:
        query = " ".join(args).strip()
        if not query:
            return "Usage: /memory search <query>"
        memories = MemoryStore(self.root).search(query, limit=5)
        if not memories:
            return "No memories found."
        return "\n".join(
            f"{memory.id} {memory.project} {memory.kind} {memory.title}" for memory in memories
        )


def _help_text() -> str:
    return "\n".join(
        [
            "Commands:",
            "help, version, doctor, exit, quit",
            "/model, /model list, /model set <profile>",
            "/effort low|medium|high|max",
            "/stream on|off|status",
            "/usage, /usage reset --confirm",
            "/agents, /clear, /dashboard",
            "/memory search <query>",
            "/memory on|off",
            "/brain on|off",
            "/context show|clear|status",
            "/retrieve memory <query>",
            "/retrieve brain <query>",
            "Any other input is sent to the active model.",
            "Retrieval is explicit opt-in; traces and files are not included automatically.",
        ]
    )


def _needs_context_warning(usage: ContextUsage) -> bool:
    return usage.status in {"warn", "critical"} and usage.used_percent is not None


def _rounded_percent(usage: ContextUsage) -> float | None:
    if usage.used_percent is None:
        return None
    return round(usage.used_percent, 2)
