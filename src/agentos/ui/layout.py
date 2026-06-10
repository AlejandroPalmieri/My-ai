from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field
from rich import box
from rich.columns import Columns
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agentos import __version__
from agentos.context.schemas import ContextUsage
from agentos.models.pricing import format_estimated_cost
from agentos.ui.theme import Theme


class ModelStatusSummary(BaseModel):
    active_model_profile: str = "local-stub"
    active_provider: str = "local"
    active_model: str = "local-stub"
    effort: str = "low"
    context_window_tokens: int = 0
    context_used_tokens: int = 0
    context_used_percent: float | None = None
    context_usage: ContextUsage | None = None
    cumulative_input_tokens: int = 0
    cumulative_output_tokens: int = 0
    cumulative_total_tokens: int = 0
    cumulative_estimated_cost_usd: float | None = None
    current_session_estimated_cost_usd: float | None = None
    daily_estimated_cost_usd: float | None = None
    status: str = "configured"
    warnings: list[str] = Field(default_factory=list)


class RuntimeInfo(BaseModel):
    version: str = __version__
    active_profile: str
    workspace: Path
    model_status: ModelStatusSummary = Field(default_factory=ModelStatusSummary)
    memory_status: str
    skill_registry_status: str
    policy_status: str
    sdd_status: str
    memory_db_path: Path
    skill_registry_path: Path
    policy_files: list[Path]
    warnings: list[str]


class MemorySummary(BaseModel):
    id: str
    project: str
    title: str
    kind: str
    updated_at: str


class SDDChangeSummary(BaseModel):
    name: str
    phase: str
    archived: bool


class TraceSummary(BaseModel):
    event_type: str
    command: str
    status: str
    timestamp: str


class SkillSummary(BaseModel):
    name: str
    path: str
    valid: bool


class PolicyViolationSummary(BaseModel):
    command: str
    status: str
    matched_rule: str
    timestamp: str


class AgentSummary(BaseModel):
    id: str
    name: str
    role: str
    kind: str
    status: str
    model_profile: str
    effort: str
    parent_id: str | None = None
    current_task: str
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float | None = None


class DashboardData(BaseModel):
    runtime: RuntimeInfo
    memory_count: int
    recent_memories: list[MemorySummary]
    active_sdd_changes: list[SDDChangeSummary]
    registered_skills: list[SkillSummary]
    recent_policy_violations: list[PolicyViolationSummary]
    recent_traces: list[TraceSummary]
    agents: list[AgentSummary] = Field(default_factory=list)


def render_header(runtime: RuntimeInfo, theme: Theme) -> RenderableType:
    text = Text()
    text.append(" AGENTOS PERSONAL ", style=theme.style("primary", bold=True))
    text.append("| ", style=theme.style("muted"))
    text.append(runtime.active_profile, style=theme.style("secondary"))
    text.append(" | ", style=theme.style("muted"))
    text.append(runtime.workspace.name or str(runtime.workspace), style=theme.style("text"))
    text.append(" | ", style=theme.style("muted"))
    text.append(f"v{runtime.version}", style=theme.style("muted"))
    return Panel(
        text,
        border_style=theme.style("border_active"),
        style=theme.style("surface"),
        box=box.SQUARE,
        padding=(0, 1),
    )


def render_navigation(theme: Theme) -> Panel:
    table = Table.grid(padding=(0, 1))
    for item in ["Memory", "SDD", "Skills", "Policies", "Traces", "Profiles"]:
        marker = ">" if item == "Memory" else " "
        style = theme.style("primary", bold=True) if item == "Memory" else theme.style("text")
        table.add_row(Text(marker, style=theme.style("border_active")), Text(item, style=style))
    return Panel(
        table,
        title="Navigation",
        border_style=theme.style("border_active"),
        style=theme.style("panel"),
        box=box.SQUARE,
    )


def render_workspace_overview(data: DashboardData, theme: Theme) -> Panel:
    table = Table.grid(expand=True)
    table.add_column(ratio=1)
    table.add_row(_section_title("status", theme))
    table.add_row(f"Memory count | {data.memory_count}")
    table.add_row(f"Registered skills | {len(data.registered_skills)}")
    table.add_row("")
    table.add_row(_section_title("recent memories", theme))
    if data.recent_memories:
        for memory in data.recent_memories:
            table.add_row(f"{memory.project} | {memory.kind} | {memory.title}")
    else:
        table.add_row(Text("No memories yet", style=theme.style("muted")))
    table.add_row("")
    table.add_row(_section_title("active SDD changes", theme))
    if data.active_sdd_changes:
        for change in data.active_sdd_changes:
            table.add_row(f"{change.name} | {change.phase}")
    else:
        table.add_row(Text("No active changes", style=theme.style("muted")))
    table.add_row("")
    table.add_row(_section_title("registered skills", theme))
    if data.registered_skills:
        for skill in data.registered_skills[:5]:
            valid = "valid" if skill.valid else "invalid"
            table.add_row(f"{skill.name} | {valid}")
    else:
        table.add_row(Text("No registered skills", style=theme.style("muted")))
    table.add_row("")
    table.add_row(_section_title("recent policy violations", theme))
    if data.recent_policy_violations:
        for violation in data.recent_policy_violations:
            table.add_row(
                f"{violation.command} | {violation.status} | {violation.matched_rule}"
            )
    else:
        table.add_row(Text("No recent policy violations", style=theme.style("muted")))
    table.add_row("")
    table.add_row(_section_title("latest trace events", theme))
    if data.recent_traces:
        for event in data.recent_traces:
            table.add_row(f"{event.event_type} | {event.command} | {event.status}")
    else:
        table.add_row(Text("No trace events", style=theme.style("muted")))
    return Panel(
        table,
        title="Workspace Overview",
        border_style=theme.style("border_active"),
        style=theme.style("panel"),
        box=box.SQUARE,
    )


def render_agents_runtime(data: DashboardData, theme: Theme) -> Panel:
    table = Table.grid(padding=(0, 1))
    table.add_column(style=theme.style("muted"))
    table.add_column(style=theme.style("text"))
    table.add_row(_section_title("agents", theme), "")
    if data.agents:
        for agent in data.agents[:8]:
            parent = f" parent={agent.parent_id}" if agent.parent_id else ""
            usage = (
                f" tok={agent.input_tokens}/{agent.output_tokens} "
                f"cost={format_estimated_cost(agent.estimated_cost_usd)}"
            )
            table.add_row(
                f"{agent.name}",
                (
                    f"{agent.kind} | {agent.status} | {agent.role} | "
                    f"{agent.model_profile} | {agent.effort}{parent}{usage}"
                ),
            )
            table.add_row("task", agent.current_task)
    else:
        table.add_row("status", "no active agents")
    table.add_row("", "")
    table.add_row(_section_title("runtime", theme), "")
    runtime = data.runtime
    table.add_row("active profile", runtime.active_profile)
    table.add_row("model", runtime.model_status.active_model)
    table.add_row("provider", runtime.model_status.active_provider)
    table.add_row("effort", runtime.model_status.effort)
    table.add_row("context", format_model_context(runtime.model_status))
    table.add_row("tokens", format_model_token_ratio(runtime.model_status))
    table.add_row("cost", format_model_cost(runtime.model_status))
    table.add_row("memory db", str(runtime.memory_db_path))
    table.add_row("skill registry", str(runtime.skill_registry_path))
    table.add_row("policy files", str(len(runtime.policy_files)))
    table.add_row("memory", runtime.memory_status)
    table.add_row("skills", runtime.skill_registry_status)
    table.add_row("policies", runtime.policy_status)
    table.add_row("sdd", runtime.sdd_status)
    if runtime.warnings:
        table.add_row("warnings", "; ".join(runtime.warnings))
    else:
        table.add_row("warnings", "none")
    return Panel(
        table,
        title="Agents / Subagents",
        border_style=theme.style("border"),
        style=theme.style("panel"),
        box=box.SQUARE,
    )


def render_bottom_bar(
    model_status: ModelStatusSummary,
    theme: Theme,
    *,
    compact: bool = False,
) -> RenderableType:
    if compact:
        return Panel(
            Text(
                _compact_model_status(model_status),
                style=_model_runtime_style(model_status, theme),
            ),
            border_style=theme.style("border"),
            style=theme.style("surface"),
            box=box.SQUARE,
            padding=(0, 1),
        )

    keybindings = Text()
    for label in [
        "[q] quit",
        "[tab] pane",
        "[r] refresh",
        "[b] backup",
        "[e] eval",
        "[k] scan skills",
        "[m/s/p/t] focus",
    ]:
        keybindings.append(f" {label} ", style=theme.style("secondary"))
        keybindings.append("|", style=theme.style("border"))
    keybindings.rstrip()
    model_text = Text(
        _full_model_status(model_status),
        style=_model_runtime_style(model_status, theme),
    )
    return Panel(
        Group(keybindings, model_text),
        border_style=theme.style("border"),
        style=theme.style("surface"),
        box=box.SQUARE,
        padding=(0, 1),
    )


def render_dashboard_layout(
    data: DashboardData,
    theme: Theme,
    *,
    compact: bool = False,
) -> RenderableType:
    navigation = render_navigation(theme)
    overview = render_workspace_overview(data, theme)
    runtime = render_agents_runtime(data, theme)
    if compact:
        body: RenderableType = Group(navigation, overview, runtime)
    else:
        body = Columns([navigation, overview, runtime], expand=True, equal=False)
    return Group(
        render_header(data.runtime, theme),
        body,
        render_bottom_bar(data.runtime.model_status, theme, compact=compact),
    )


def render_plain_dashboard(data: DashboardData) -> str:
    header = (
        f"AGENTOS PERSONAL | {data.runtime.active_profile} | "
        f"{data.runtime.workspace} | v{data.runtime.version}"
    )
    lines = [
        header,
        "Navigation: Memory, SDD, Skills, Policies, Traces, Profiles",
        "Workspace Overview",
        f"Active profile: {data.runtime.active_profile}",
        f"Memory count: {data.memory_count}",
        "Recent memories:",
    ]
    lines.extend(
        f"- {memory.project} | {memory.kind} | {memory.title}" for memory in data.recent_memories
    )
    if not data.recent_memories:
        lines.append("- none")
    lines.append("Active SDD changes:")
    lines.extend(f"- {change.name} | {change.phase}" for change in data.active_sdd_changes)
    if not data.active_sdd_changes:
        lines.append("- none")
    lines.append("Registered skills:")
    lines.extend(f"- {skill.name} | {skill.path}" for skill in data.registered_skills[:10])
    if not data.registered_skills:
        lines.append("- none")
    lines.append("Recent policy violations:")
    lines.extend(
        f"- {violation.command} | {violation.status} | {violation.matched_rule}"
        for violation in data.recent_policy_violations
    )
    if not data.recent_policy_violations:
        lines.append("- none")
    lines.append("Latest trace events:")
    lines.extend(
        f"- {event.event_type} | {event.command} | {event.status}" for event in data.recent_traces
    )
    if not data.recent_traces:
        lines.append("- none")
    lines.append("Agents / Subagents")
    if data.agents:
        for agent in data.agents:
            parent = f" | parent: {agent.parent_id}" if agent.parent_id else ""
            usage = (
                f" | tokens: {agent.input_tokens}/{agent.output_tokens} "
                f"| cost: {format_estimated_cost(agent.estimated_cost_usd)}"
            )
            lines.append(
                f"- {agent.name} | {agent.kind} | {agent.status} | "
                f"{agent.model_profile} | {agent.effort} | {agent.current_task}"
                f"{parent}{usage}"
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "Runtime Context",
            f"- active profile: {data.runtime.active_profile}",
            f"- memory database path: {data.runtime.memory_db_path}",
            f"- skill registry path: {data.runtime.skill_registry_path}",
            f"- policy files: {len(data.runtime.policy_files)}",
            f"- warnings: {'; '.join(data.runtime.warnings) if data.runtime.warnings else 'none'}",
            "Model Runtime",
            f"- model: {data.runtime.model_status.active_model}",
            f"- provider: {data.runtime.model_status.active_provider}",
            f"- effort: {data.runtime.model_status.effort}",
            f"- context: {format_model_context(data.runtime.model_status)}",
            f"- tokens: {format_model_token_ratio(data.runtime.model_status)}",
            f"- cumulative input tokens: "
            f"{data.runtime.model_status.cumulative_input_tokens}",
            f"- cumulative output tokens: "
            f"{data.runtime.model_status.cumulative_output_tokens}",
            f"- cumulative total tokens: "
            f"{data.runtime.model_status.cumulative_total_tokens}",
            f"- cumulative estimated cost: {format_model_cost(data.runtime.model_status)}",
            f"- current session estimated cost: "
            f"{format_model_session_cost(data.runtime.model_status)}",
            f"- daily estimated cost: {format_model_daily_cost(data.runtime.model_status)}",
            "[q] quit | [tab] pane | [r] refresh | [b] backup | [e] eval | "
            "[k] scan skills | [m/s/p/t] focus    "
            f"{_full_model_status(data.runtime.model_status)}",
        ]
    )
    return "\n".join(lines)


def _section_title(label: str, theme: Theme) -> Text:
    return Text(label.upper(), style=theme.style("secondary", bold=True))


def _full_model_status(model_status: ModelStatusSummary) -> str:
    return (
        f"model: {model_status.active_model}|"
        f"provider: {model_status.active_provider}|"
        f"effort: {model_status.effort}|"
        f"ctx: {format_model_context(model_status)}|"
        f"tok: {format_model_token_ratio(model_status)}|"
        f"cost: {format_model_cost(model_status)}|"
        f"i/o/t: {model_status.cumulative_input_tokens}/"
        f"{model_status.cumulative_output_tokens}/"
        f"{model_status.cumulative_total_tokens}\n"
        f"session: {format_model_session_cost(model_status)}|"
        f"today: {format_model_daily_cost(model_status)}"
    )


def _compact_model_status(model_status: ModelStatusSummary) -> str:
    return (
        f"model: {model_status.active_model} | "
        f"effort: {model_status.effort} | "
        f"ctx: {format_model_context(model_status)} | "
        f"cost: {format_model_cost(model_status)} | "
        f"session: {format_model_session_cost(model_status)} | "
        f"today: {format_model_daily_cost(model_status)}"
    )


def format_model_context(model_status: ModelStatusSummary) -> str:
    if model_status.context_usage is not None:
        if model_status.context_usage.used_percent is None:
            return "n/a"
        return f"{model_status.context_usage.used_percent:.2f}%"
    if model_status.context_window_tokens <= 0:
        return "n/a"
    value = model_status.context_used_percent
    if value is None:
        value = (model_status.context_used_tokens / model_status.context_window_tokens) * 100
    return f"{value:.2f}%"


def format_model_token_ratio(model_status: ModelStatusSummary) -> str:
    used_tokens = model_status.context_used_tokens
    if model_status.context_usage is not None:
        used_tokens = model_status.context_usage.total_estimated_tokens
    if model_status.context_window_tokens <= 0:
        return f"{_format_token_count(used_tokens)}/n/a"
    return (
        f"{_format_token_count(used_tokens)}/"
        f"{_format_token_count(model_status.context_window_tokens)}"
    )


def _format_token_count(value: int) -> str:
    if abs(value) >= 1_000:
        return f"{value / 1_000:.1f}k"
    return str(value)


def format_model_cost(model_status: ModelStatusSummary) -> str:
    return format_estimated_cost(model_status.cumulative_estimated_cost_usd)


def format_model_session_cost(model_status: ModelStatusSummary) -> str:
    return format_estimated_cost(model_status.current_session_estimated_cost_usd)


def format_model_daily_cost(model_status: ModelStatusSummary) -> str:
    return format_estimated_cost(model_status.daily_estimated_cost_usd)


def _model_runtime_style(model_status: ModelStatusSummary, theme: Theme) -> str:
    if model_status.context_usage is None:
        return theme.style("primary")
    if model_status.context_usage.status == "critical":
        return theme.style("danger", bold=True)
    if model_status.context_usage.status == "warn":
        return theme.style("warning", bold=True)
    return theme.style("primary")
