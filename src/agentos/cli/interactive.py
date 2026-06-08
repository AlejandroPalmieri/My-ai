from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from agentos import __version__


def run_interactive_cli(
    root: Path,
    forwarded_args: list[str],
    console: Console,
) -> None:
    console.print("AgentOS Interactive CLI")
    console.print("Type 'help' for commands, or 'exit' to quit.")
    if forwarded_args:
        console.print("Forwarded options: " + " ".join(forwarded_args))

    while True:
        try:
            command = typer.prompt("agentos", default="", show_default=False)
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        normalized = command.strip().lower()
        if normalized in {"exit", "quit"}:
            break
        if normalized == "help":
            _print_help(console)
        elif normalized == "version":
            console.print(f"AgentOS Personal {__version__}")
        elif normalized == "doctor":
            console.print(f"Run `agentos doctor --root {root}` for the full diagnostic report.")
        elif normalized:
            console.print(f"Unknown interactive command: {command}")


def _print_help(console: Console) -> None:
    console.print("Commands: help, version, doctor, exit")
