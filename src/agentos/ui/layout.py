from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel
from rich import box
from rich.columns import Columns
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agentos import __version__
from agentos.ui.theme import Theme


class RuntimeInfo(BaseModel):
    version: str = __version__
    active_profile: str
    workspace: Path
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


class DashboardData(BaseModel):
    runtime: RuntimeInfo
    memory_count: int
    recent_memories: list[MemorySummary]
    active_sdd_changes: list[SDDChangeSummary]
    registered_skills: list[SkillSummary]
    recent_policy_violations: list[PolicyViolationSummary]
    recent_traces: list[TraceSummary]


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


def render_runtime_context(runtime: RuntimeInfo, theme: Theme) -> Panel:
    table = Table.grid(padding=(0, 1))
    table.add_column(style=theme.style("muted"))
    table.add_column(style=theme.style("text"))
    table.add_row("active profile", runtime.active_profile)
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
        title="Runtime Context",
        border_style=theme.style("border"),
        style=theme.style("panel"),
        box=box.SQUARE,
    )


def render_bottom_bar(theme: Theme) -> RenderableType:
    text = Text()
    for label in [
        "[q] quit",
        "[tab] pane",
        "[r] refresh",
        "[b] backup",
        "[e] eval",
        "[k] scan skills",
        "[m/s/p/t] focus",
    ]:
        text.append(f" {label} ", style=theme.style("secondary"))
        text.append("|", style=theme.style("border"))
    text.rstrip()
    return Panel(
        text,
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
    runtime = render_runtime_context(data.runtime, theme)
    if compact:
        body: RenderableType = Group(navigation, overview, runtime)
    else:
        body = Columns([navigation, overview, runtime], expand=True, equal=False)
    return Group(render_header(data.runtime, theme), body, render_bottom_bar(theme))


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
    lines.extend(
        [
            "Runtime Context",
            f"- active profile: {data.runtime.active_profile}",
            f"- memory database path: {data.runtime.memory_db_path}",
            f"- skill registry path: {data.runtime.skill_registry_path}",
            f"- policy files: {len(data.runtime.policy_files)}",
            f"- warnings: {'; '.join(data.runtime.warnings) if data.runtime.warnings else 'none'}",
            "[q] quit | [tab] pane | [r] refresh | [b] backup | [e] eval | "
            "[k] scan skills | [m/s/p/t] focus",
        ]
    )
    return "\n".join(lines)


def _section_title(label: str, theme: Theme) -> Text:
    return Text(label.upper(), style=theme.style("secondary", bold=True))
