from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from agentos.cli.interactive_chat import InteractiveChatSession
from agentos.config.settings import load_config
from agentos.ui.banner import render_startup_banner
from agentos.ui.dashboard import collect_dashboard_data, render_dashboard
from agentos.ui.theme import load_theme


def run_interactive_cli(
    root: Path,
    forwarded_args: list[str],
    console: Console,
    show_banner: bool | None = None,
    show_dashboard: bool | None = None,
    plain: bool = False,
    theme_name: str | None = None,
) -> None:
    config = load_config(root)
    effective_theme_name = theme_name or config.ui.theme
    try:
        theme = load_theme(effective_theme_name)
    except KeyError:
        theme = load_theme("zellij-neutral")
        console.print(f"Unknown theme '{effective_theme_name}', using zellij-neutral.")

    should_show_banner = config.ui.show_banner if show_banner is None else show_banner
    should_show_dashboard = (
        config.ui.open_dashboard_on_start if show_dashboard is None else show_dashboard
    )
    plain_mode = plain or console.color_system is None
    data = collect_dashboard_data(root)
    if should_show_banner:
        console.print(render_startup_banner(data.runtime, theme, plain=plain_mode))
    if should_show_dashboard:
        compact = _should_use_compact_layout(config.ui.compact_mode, console.width)
        console.print(render_dashboard(data, theme, compact=compact, plain=plain_mode))

    session = InteractiveChatSession(
        root,
        max_history_messages=config.chat.max_history_messages,
    )
    console.print("AgentOS Interactive Model Chat")
    console.print("Type 'help' for commands, or 'exit' to quit.")
    if forwarded_args:
        console.print("Forwarded options: " + " ".join(forwarded_args))

    while True:
        try:
            command = typer.prompt("agentos", default="", show_default=False)
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        result = session.handle_input(command)
        if result.dashboard_requested:
            data = collect_dashboard_data(root)
            compact = _should_use_compact_layout(config.ui.compact_mode, console.width)
            console.print(render_dashboard(data, theme, compact=compact, plain=plain_mode))
        if result.output:
            console.print(result.output, markup=False)
        if result.should_exit:
            break


def _should_use_compact_layout(compact_mode: str, width: int) -> bool:
    if compact_mode == "true":
        return True
    if compact_mode == "false":
        return False
    return width < 100
