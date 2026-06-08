from __future__ import annotations

from rich import box
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agentos.ui.layout import RuntimeInfo
from agentos.ui.theme import Theme

SUBTITLE = "Personal Agent Operating System"


def render_startup_banner(
    runtime: RuntimeInfo,
    theme: Theme,
    *,
    plain: bool = False,
) -> RenderableType | str:
    if plain:
        return _plain_banner(runtime)

    logo = Text("AGENTOS", style=theme.style("primary", bold=True))
    subtitle = Text(SUBTITLE, style=theme.style("secondary"))
    runtime_panel = Table.grid(padding=(0, 2))
    runtime_panel.add_column(style=theme.style("muted"))
    runtime_panel.add_column(style=theme.style("text"))
    runtime_panel.add_row("version", runtime.version)
    runtime_panel.add_row("active profile", runtime.active_profile)
    runtime_panel.add_row("current workspace", str(runtime.workspace))
    runtime_panel.add_row("memory status", runtime.memory_status)
    runtime_panel.add_row("skill registry status", runtime.skill_registry_status)
    runtime_panel.add_row("policy status", runtime.policy_status)
    runtime_panel.add_row("SDD status", runtime.sdd_status)
    return Panel(
        Group(logo, subtitle, runtime_panel),
        border_style=theme.style("border_active"),
        style=theme.style("surface"),
        box=box.SQUARE,
        padding=(1, 2),
    )


def _plain_banner(runtime: RuntimeInfo) -> str:
    return "\n".join(
        [
            "AGENTOS",
            SUBTITLE,
            f"version: {runtime.version}",
            f"active profile: {runtime.active_profile}",
            f"current workspace: {runtime.workspace}",
            f"memory status: {runtime.memory_status}",
            f"skill registry status: {runtime.skill_registry_status}",
            f"policy status: {runtime.policy_status}",
            f"SDD status: {runtime.sdd_status}",
        ]
    )
