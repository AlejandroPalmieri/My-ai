# Design: add-interactive-default

## Architecture

The console-script entrypoint changes from the raw Typer app to `agentos.cli.app:main`. The wrapper receives the raw argument list before Click/Typer parses it. If the invocation contains no known top-level subcommand, it extracts `--root`, forwards the remaining arguments to the interactive CLI, and records an `interactive` trace. Otherwise it delegates to the existing Typer app unchanged.

`src/agentos/cli/interactive.py` owns the interactive loop so `app.py` remains focused on command routing. The loop is intentionally small and local: banner, forwarded options display, `help`, `version`, `doctor` hint, and `exit`.

## Interfaces

- Console script: `agentos = "agentos.cli.app:main"`.
- No-subcommand behavior: `agentos` starts the interactive CLI.
- Forwarding behavior: `agentos --model local --profile godot` starts the interactive CLI and forwards `--model local --profile godot`.
- Existing subcommands: `agentos version`, `agentos doctor`, `agentos memory ...`, and other known commands continue through Typer.

## Safety

Interactive mode does not execute arbitrary terminal commands, read secrets, call models, or perform autonomous actions. It only prints local information and directs users to existing explicit commands. Unknown options are displayed as forwarded arguments, not executed.
