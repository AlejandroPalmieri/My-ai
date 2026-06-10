import json
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from agentos import __version__
from agentos.agents.registry import AgentRuntimeRegistry
from agentos.agents.schemas import AgentKind
from agentos.cli.interactive import run_interactive_cli
from agentos.config.profiles import ProjectProfile
from agentos.config.project import init_project
from agentos.config.settings import set_banner_visibility, set_theme
from agentos.evals.runner import EvalRunner
from agentos.logging.traces import (
    TraceEventType,
    TraceLogger,
)
from agentos.mcp.server import serve_stdio
from agentos.models.client import chat_once
from agentos.models.config import (
    create_default_model_config,
    inspect_model_status,
    load_model_config,
    reset_usage,
    set_active_model_profile,
)
from agentos.models.effort import EFFORT_PROFILES, get_effort_profile
from agentos.models.pricing import format_estimated_cost
from agentos.models.routing import load_routing_config, set_route
from agentos.refiner.analyzer import RefinerAnalysis
from agentos.sdd.generator import InvalidPhaseTransitionError, InvalidSlugError
from agentos.services.container import ServiceContainer, create_service_container
from agentos.ui.banner import render_startup_banner
from agentos.ui.dashboard import collect_dashboard_data, render_dashboard
from agentos.ui.interactive import run_interactive_dashboard
from agentos.ui.theme import list_themes, load_theme
from agentos.usage.schemas import UsageSummary
from agentos.usage.store import UsageStore

ROOT_CONTEXT_SETTINGS = {"allow_extra_args": True, "ignore_unknown_options": True}
app = typer.Typer(
    help="AgentOS Personal local-first agent operating system.",
    context_settings=ROOT_CONTEXT_SETTINGS,
)
memory_app = typer.Typer(help="Technical memory commands.")
brain_app = typer.Typer(help="Strategic document index commands.")
sdd_app = typer.Typer(help="SDD/OpenSpec artifact commands.")
skills_app = typer.Typer(help="Skill registry commands.")
policies_app = typer.Typer(help="Policy checking commands.")
traces_app = typer.Typer(help="Trace log commands.")
profile_app = typer.Typer(help="Project profile commands.")
ui_app = typer.Typer(help="Terminal UI commands.")
mcp_app = typer.Typer(help="Experimental local MCP server commands.")
eval_app = typer.Typer(help="Local evaluation commands.")
refiner_app = typer.Typer(help="Controlled refiner proposal commands.")
backup_app = typer.Typer(help="Local backup and rollback commands.")
models_app = typer.Typer(help="Model provider configuration commands.")
models_effort_app = typer.Typer(help="Model effort profile commands.")
models_route_app = typer.Typer(help="Model routing rule commands.")
chat_app = typer.Typer(help="Single-turn model chat commands.")
agents_app = typer.Typer(help="Local agent runtime registry commands.")
usage_app = typer.Typer(help="Token and cost usage accounting commands.")
console = Console()
RootOption = Annotated[Path, typer.Option("--root", help="Project root.")]
TOP_LEVEL_COMMANDS = {
    "version",
    "init",
    "doctor",
    "memory",
    "brain",
    "sdd",
    "skills",
    "policies",
    "traces",
    "profile",
    "dashboard",
    "ui",
    "mcp",
    "eval",
    "refiner",
    "backup",
    "models",
    "chat",
    "agents",
    "usage",
}
TYPER_ROOT_OPTIONS = {"--help", "-h", "--install-completion", "--show-completion"}
STARTUP_BOOL_OPTIONS = {"--no-banner", "--no-dashboard", "--plain"}
STARTUP_VALUE_OPTIONS = {"--root", "--theme"}


@app.callback(invoke_without_command=True, context_settings=ROOT_CONTEXT_SETTINGS)
def root_callback(
    ctx: typer.Context,
    root: RootOption = Path("."),
    no_banner: Annotated[bool, typer.Option("--no-banner", help="Hide startup banner.")] = False,
    no_dashboard: Annotated[
        bool,
        typer.Option("--no-dashboard", help="Hide startup dashboard."),
    ] = False,
    plain: Annotated[bool, typer.Option("--plain", help="Use plain text startup UI.")] = False,
    theme: Annotated[str | None, typer.Option("--theme", help="Startup UI theme.")] = None,
) -> None:
    """Run the interactive CLI when no subcommand is specified."""
    if ctx.invoked_subcommand is not None:
        return
    trace = _start_trace(root, "interactive")
    run_interactive_cli(
        root,
        list(ctx.args),
        console,
        show_banner=not no_banner,
        show_dashboard=not no_dashboard,
        plain=plain,
        theme_name=theme,
    )
    _complete_trace(trace, "interactive", {"forwarded_arg_count": len(ctx.args)})


def main(args: list[str] | None = None) -> None:
    """Console-script entrypoint that forwards no-subcommand invocations."""
    cli_args = list(sys.argv[1:] if args is None else args)
    if _should_run_interactive(cli_args):
        root, forwarded_args, show_banner, show_dashboard, plain, theme_name = (
            _extract_interactive_args(cli_args)
        )
        trace = _start_trace(root, "interactive")
        run_interactive_cli(
            root,
            forwarded_args,
            console,
            show_banner=show_banner,
            show_dashboard=show_dashboard,
            plain=plain,
            theme_name=theme_name,
        )
        _complete_trace(trace, "interactive", {"forwarded_arg_count": len(forwarded_args)})
        return
    app(args=cli_args, prog_name="agentos")


def _should_run_interactive(args: list[str]) -> bool:
    if any(arg in TYPER_ROOT_OPTIONS for arg in args):
        return False
    index = _first_non_root_option_index(args)
    if index >= len(args):
        return True
    return args[index] not in TOP_LEVEL_COMMANDS


def _extract_interactive_args(
    args: list[str],
) -> tuple[Path, list[str], bool, bool, bool, str | None]:
    root = Path(".")
    forwarded_args: list[str] = []
    show_banner = True
    show_dashboard = True
    plain = False
    theme_name: str | None = None
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--root" and index + 1 < len(args):
            root = Path(args[index + 1])
            index += 2
        elif arg.startswith("--root="):
            root = Path(arg.split("=", 1)[1])
            index += 1
        elif arg == "--theme" and index + 1 < len(args):
            theme_name = args[index + 1]
            index += 2
        elif arg.startswith("--theme="):
            theme_name = arg.split("=", 1)[1]
            index += 1
        elif arg == "--no-banner":
            show_banner = False
            index += 1
        elif arg == "--no-dashboard":
            show_dashboard = False
            index += 1
        elif arg == "--plain":
            plain = True
            index += 1
        else:
            forwarded_args.append(arg)
            index += 1
    return root, forwarded_args, show_banner, show_dashboard, plain, theme_name


def _first_non_root_option_index(args: list[str]) -> int:
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in STARTUP_VALUE_OPTIONS:
            index += 2
        elif any(arg.startswith(f"{option}=") for option in STARTUP_VALUE_OPTIONS):
            index += 1
        elif arg in STARTUP_BOOL_OPTIONS:
            index += 1
        else:
            break
    return index


@app.command()
def version() -> None:
    """Show the AgentOS Personal version."""
    console.print(f"AgentOS Personal {__version__}")


@app.command()
def init(root: RootOption = Path(".")) -> None:
    """Create local AgentOS directories and default policy files."""
    trace = _start_trace(root, "init")
    created = init_project(root)
    _complete_trace(trace, "init")
    console.print(f"Initialized AgentOS project at {created.root}")


@app.command()
def doctor(root: RootOption = Path(".")) -> None:
    """Diagnose the local AgentOS environment."""
    trace = _start_trace(root, "doctor")
    report = _services(root).doctor.run()
    _print_doctor_report(report)
    _complete_trace(trace, "doctor", {"healthy": report.healthy})
    if not report.healthy:
        raise typer.Exit(1)


@app.command("dashboard")
def dashboard_command(
    theme: Annotated[str, typer.Option("--theme", help="Dashboard theme.")] = "zellij-neutral",
    plain: Annotated[bool, typer.Option("--plain", help="Use plain text output.")] = False,
    interactive: Annotated[
        bool,
        typer.Option("--interactive", help="Enable keyboard-driven dashboard controls."),
    ] = False,
    once: Annotated[
        bool,
        typer.Option("--once", help="Render interactive dashboard once and exit."),
    ] = False,
    root: RootOption = Path("."),
) -> None:
    """Render the terminal dashboard."""
    trace = _start_trace(root, "dashboard")
    try:
        ui_theme = load_theme(theme)
    except KeyError as error:
        _fail_trace(trace, "dashboard", str(error))
        console.print(str(error))
        raise typer.Exit(1) from error
    plain_output = plain or console.color_system is None
    if interactive:
        run_interactive_dashboard(root, console, ui_theme, plain=plain_output, once=once)
        _complete_trace(trace, "dashboard", {"theme": ui_theme.name, "interactive": True})
        return
    data = collect_dashboard_data(root)
    compact = console.width < 100
    rendered = render_dashboard(
        data,
        ui_theme,
        compact=compact,
        plain=plain_output,
    )
    console.print(rendered, markup=not isinstance(rendered, str))
    _complete_trace(trace, "dashboard", {"theme": ui_theme.name})


@ui_app.command("preview")
def ui_preview(
    theme: Annotated[str, typer.Option("--theme", help="UI theme.")] = "zellij-neutral",
    plain: Annotated[bool, typer.Option("--plain", help="Use plain text output.")] = False,
    root: RootOption = Path("."),
) -> None:
    """Preview the startup banner and dashboard."""
    trace = _start_trace(root, "ui.preview")
    try:
        ui_theme = load_theme(theme)
    except KeyError as error:
        _fail_trace(trace, "ui.preview", str(error))
        console.print(str(error))
        raise typer.Exit(1) from error
    data = collect_dashboard_data(root)
    compact = console.width < 100
    console.print(render_startup_banner(data.runtime, ui_theme, plain=plain))
    console.print(render_dashboard(data, ui_theme, compact=compact, plain=plain))
    _complete_trace(trace, "ui.preview", {"theme": ui_theme.name})


@ui_app.command("themes")
def ui_themes(root: RootOption = Path(".")) -> None:
    """List available terminal UI themes."""
    trace = _start_trace(root, "ui.themes")
    table = Table("Name", "Description")
    themes = list_themes()
    for theme in themes:
        table.add_row(theme.name, theme.description)
    console.print(table)
    _complete_trace(trace, "ui.themes", {"count": len(themes)})


@ui_app.command("set-theme")
def ui_set_theme(
    theme_name: Annotated[str, typer.Argument(help="Theme name.")],
    root: RootOption = Path("."),
) -> None:
    """Set the default startup UI theme."""
    trace = _start_trace(root, "ui.set-theme")
    try:
        load_theme(theme_name)
    except KeyError as error:
        _fail_trace(trace, "ui.set-theme", str(error))
        console.print(str(error))
        raise typer.Exit(1) from error
    set_theme(root, theme_name)
    console.print(f"UI theme set to {theme_name}")
    _complete_trace(trace, "ui.set-theme", {"theme": theme_name})


@ui_app.command("banner")
def ui_banner(
    show: Annotated[bool, typer.Option("--show", help="Show startup banner.")] = False,
    hide: Annotated[bool, typer.Option("--hide", help="Hide startup banner.")] = False,
    root: RootOption = Path("."),
) -> None:
    """Show or hide the startup banner."""
    trace = _start_trace(root, "ui.banner")
    if show and hide:
        _fail_trace(trace, "ui.banner", "Choose --show or --hide, not both.")
        raise typer.BadParameter("Choose --show or --hide, not both.")
    if not show and not hide:
        console.print("Use --show or --hide.")
        _complete_trace(trace, "ui.banner", {"changed": False})
        return
    visible = show and not hide
    set_banner_visibility(root, visible)
    console.print(f"Startup banner {'shown' if visible else 'hidden'}")
    _complete_trace(trace, "ui.banner", {"show_banner": visible})


@mcp_app.command("serve")
def mcp_serve(root: RootOption = Path(".")) -> None:
    """Serve AgentOS local capabilities over MCP STDIO."""
    serve_stdio(root)


@models_app.command("init")
def models_init(root: RootOption = Path(".")) -> None:
    """Create the local model provider configuration file."""
    trace = _start_trace(root, "models.init")
    path = create_default_model_config(root)
    console.print(f"Model config initialized at {path}")
    _complete_trace(trace, "models.init", {"path": str(path)})


@models_effort_app.command("list")
def models_effort_list(root: RootOption = Path(".")) -> None:
    """List built-in effort profile definitions."""
    trace = _start_trace(root, "models.effort.list")
    table = Table("Effort", "Description", "Temperature", "Max Output", "Use")
    for profile in EFFORT_PROFILES.values():
        table.add_row(
            profile.label,
            profile.description,
            str(profile.default_temperature),
            str(profile.default_max_output_tokens),
            profile.intended_use,
        )
    console.print(table)
    for profile in EFFORT_PROFILES.values():
        console.print(
            f"{profile.label} temp={profile.default_temperature} "
            f"max_output={profile.default_max_output_tokens}: {profile.intended_use}",
            markup=False,
        )
    _complete_trace(trace, "models.effort.list", {"count": len(EFFORT_PROFILES)})


@models_effort_app.command("show")
def models_effort_show(
    effort: Annotated[str, typer.Argument(help="Effort level.")],
    root: RootOption = Path("."),
) -> None:
    """Show one effort profile definition."""
    trace = _start_trace(root, "models.effort.show")
    try:
        profile = get_effort_profile(effort)
    except KeyError as error:
        _fail_trace(trace, "models.effort.show", str(error))
        console.print(str(error))
        raise typer.Exit(1) from error
    table = Table("Field", "Value")
    for key, value in profile.model_dump().items():
        table.add_row(key, str(value))
    console.print(table)
    _complete_trace(trace, "models.effort.show", {"effort": profile.label})


@models_route_app.command("list")
def models_route_list(root: RootOption = Path(".")) -> None:
    """List local model routing rules."""
    trace = _start_trace(root, "models.route.list")
    config = load_routing_config(root)
    table = Table("Route", "Model Profile", "Effort")
    for route_name, route in sorted(config.routes.items()):
        table.add_row(route_name, route.model_profile or "", route.effort)
    console.print(table)
    for route_name, route in sorted(config.routes.items()):
        console.print(
            f"{route_name} model={route.model_profile or ''} effort={route.effort}",
            markup=False,
        )
    _complete_trace(trace, "models.route.list", {"count": len(config.routes)})


@models_route_app.command("set")
def models_route_set(
    route_name: Annotated[str, typer.Argument(help="Route name.")],
    model_profile_name: Annotated[
        str,
        typer.Option("--model", help="Model profile for this route."),
    ],
    effort: Annotated[str, typer.Option("--effort", help="Effort level.")],
    root: RootOption = Path("."),
) -> None:
    """Set a local model routing rule."""
    trace = _start_trace(root, "models.route.set")
    try:
        config = set_route(
            root,
            route_name,
            model_profile=model_profile_name,
            effort=effort,
        )
    except (KeyError, ValueError) as error:
        _fail_trace(trace, "models.route.set", str(error))
        console.print(str(error))
        raise typer.Exit(1) from error
    route = config.routes[route_name]
    console.print(
        f"Route {route_name} set to model={route.model_profile or ''} effort={route.effort}",
        markup=False,
    )
    _complete_trace(
        trace,
        "models.route.set",
        {"route": route_name, "model_profile": route.model_profile or "", "effort": route.effort},
    )


@models_app.command("list")
def models_list(root: RootOption = Path(".")) -> None:
    """List local model providers and model profiles."""
    trace = _start_trace(root, "models.list")
    config = load_model_config(root)
    providers = Table("Provider", "Kind", "Enabled", "Base URL", "API Key Env")
    for provider in config.providers:
        providers.add_row(
            provider.name,
            provider.kind,
            str(provider.enabled),
            provider.base_url or "",
            provider.api_key_env or "",
        )
    profiles = Table(
        "Active",
        "Profile",
        "Provider",
        "Model",
        "Effort",
        "Context",
        "Input $/1M",
        "Output $/1M",
        "Enabled",
    )
    for profile in config.model_profiles:
        profiles.add_row(
            "*" if profile.name == config.active.active_model_profile else "",
            profile.name,
            profile.provider,
            profile.model,
            profile.effort,
            str(profile.context_window_tokens),
            "n/a"
            if profile.input_token_cost_per_1m is None
            else str(profile.input_token_cost_per_1m),
            "n/a"
            if profile.output_token_cost_per_1m is None
            else str(profile.output_token_cost_per_1m),
            str(profile.enabled),
        )
    console.print(providers)
    console.print(profiles)
    for provider in config.providers:
        console.print(
            f"provider {provider.name} {provider.kind} enabled={provider.enabled}",
            markup=False,
        )
    for profile in config.model_profiles:
        console.print(
            f"profile {profile.name} provider={profile.provider} model={profile.model} "
            f"effort={profile.effort} enabled={profile.enabled}",
            markup=False,
        )
    _complete_trace(
        trace,
        "models.list",
        {"providers": len(config.providers), "profiles": len(config.model_profiles)},
    )


@models_app.command("show")
def models_show(root: RootOption = Path(".")) -> None:
    """Show active model configuration."""
    trace = _start_trace(root, "models.show")
    config = load_model_config(root)
    table = Table("Field", "Value")
    table.add_row("Active model profile", config.active.active_model_profile)
    table.add_row("Active provider", config.active.active_provider)
    table.add_row("Active model", config.active.active_model)
    table.add_row("Effort", config.active.effort)
    table.add_row("Context window tokens", str(config.active.context_window_tokens))
    table.add_row("Context used tokens", str(config.active.context_used_tokens))
    table.add_row("Context used percent", f"{config.active.context_used_percent:.2f}%")
    table.add_row(
        "Cumulative estimated cost",
        format_estimated_cost(config.active.cumulative_estimated_cost_usd),
    )
    console.print(table)
    _complete_trace(
        trace,
        "models.show",
        {"active_model_profile": config.active.active_model_profile},
    )


@models_app.command("set")
def models_set(
    model_profile_name: Annotated[str, typer.Argument(help="Model profile name.")],
    root: RootOption = Path("."),
) -> None:
    """Set the active model profile."""
    trace = _start_trace(root, "models.set")
    try:
        config = set_active_model_profile(root, model_profile_name)
    except (KeyError, ValueError) as error:
        _fail_trace(trace, "models.set", str(error))
        console.print(str(error))
        raise typer.Exit(1) from error
    console.print(f"Active model profile set to {config.active.active_model_profile}")
    _complete_trace(
        trace,
        "models.set",
        {"active_model_profile": config.active.active_model_profile},
    )


@models_app.command("status")
def models_status(root: RootOption = Path(".")) -> None:
    """Inspect active provider readiness without reading secrets."""
    trace = _start_trace(root, "models.status")
    status = inspect_model_status(root)
    table = Table("Field", "Value")
    table.add_row("status", status.status)
    table.add_row("active_model_profile", status.active_model_profile)
    table.add_row("active_provider", status.active_provider)
    table.add_row("active_model", status.active_model)
    table.add_row("provider_kind", status.provider_kind)
    table.add_row("api_key_env", status.api_key_env or "")
    for warning in status.warnings:
        table.add_row("warning", warning)
    console.print(table)
    _complete_trace(trace, "models.status", {"status": status.status})


@models_app.command("usage")
def models_usage(root: RootOption = Path(".")) -> None:
    """Show cumulative local model usage estimates."""
    trace = _start_trace(root, "models.usage")
    active = load_model_config(root).active
    usage_summary = UsageStore(root).summary()
    table = Table("Field", "Value")
    table.add_row("active_model_profile", active.active_model_profile)
    table.add_row("context_used_tokens", str(active.context_used_tokens))
    table.add_row("context_used_percent", f"{active.context_used_percent:.2f}%")
    table.add_row("cumulative_input_tokens", str(active.cumulative_input_tokens))
    table.add_row("cumulative_output_tokens", str(active.cumulative_output_tokens))
    table.add_row("cumulative_total_tokens", str(active.cumulative_total_tokens))
    table.add_row(
        "cumulative_estimated_cost_usd",
        format_estimated_cost(active.cumulative_estimated_cost_usd),
    )
    table.add_row("usage_db_total_tokens", str(usage_summary.total_tokens))
    table.add_row(
        "usage_db_estimated_cost",
        format_estimated_cost(usage_summary.estimated_cost_usd),
    )
    console.print(table)
    _complete_trace(trace, "models.usage", {"total_tokens": active.cumulative_total_tokens})


@models_app.command("reset-usage")
def models_reset_usage(
    confirm: Annotated[bool, typer.Option("--confirm", help="Confirm usage reset.")] = False,
    root: RootOption = Path("."),
) -> None:
    """Reset cumulative local model usage. Requires --confirm."""
    trace = _start_trace(root, "models.reset-usage")
    try:
        reset_usage(root, confirm=confirm)
        UsageStore(root).reset(confirm=confirm)
    except ValueError as error:
        _fail_trace(trace, "models.reset-usage", str(error))
        console.print(str(error))
        raise typer.Exit(1) from error
    console.print("Usage reset")
    _complete_trace(trace, "models.reset-usage", {"reset": True})


@chat_app.command("once")
def chat_once_command(
    message: Annotated[str, typer.Argument(help="User message to send.")],
    model_profile_name: Annotated[
        str | None,
        typer.Option("--model", help="Model profile name to use for this request."),
    ] = None,
    effort: Annotated[
        str | None,
        typer.Option("--effort", help="Reasoning effort: low, medium, high, or max."),
    ] = None,
    system_prompt: Annotated[
        str | None,
        typer.Option("--system", help="Optional system prompt."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
    root: RootOption = Path("."),
) -> None:
    """Send one explicit prompt to the active model profile."""
    trace = _start_trace(root, "chat.once")
    try:
        response = chat_once(
            root,
            message=message,
            model_profile_name=model_profile_name,
            effort=effort,
            system_prompt=system_prompt,
        )
    except (KeyError, ValueError) as error:
        _fail_trace(trace, "chat.once", str(error))
        console.print(str(error))
        raise typer.Exit(1) from error
    if json_output:
        typer.echo(json.dumps(response.model_dump(mode="json"), indent=2))
    else:
        console.print(response.text, markup=False)
        console.print(
            f"model={response.model_profile} provider={response.provider} "
            f"effort={response.effort} tokens={response.usage.total_tokens} "
            f"cost={format_estimated_cost(response.usage.estimated_cost_usd)}",
            markup=False,
        )
    if response.status != "ok":
        _fail_trace(trace, "chat.once", response.error or response.text)
        raise typer.Exit(1)
    _complete_trace(
        trace,
        "chat.once",
        {"model_profile": response.model_profile, "total_tokens": response.usage.total_tokens},
    )


@chat_app.command("status")
def chat_status(root: RootOption = Path(".")) -> None:
    """Show chat provider readiness."""
    trace = _start_trace(root, "chat.status")
    status = inspect_model_status(root)
    table = Table("Field", "Value")
    table.add_row("status", status.status)
    table.add_row("active_model_profile", status.active_model_profile)
    table.add_row("active_provider", status.active_provider)
    table.add_row("active_model", status.active_model)
    table.add_row("provider_kind", status.provider_kind)
    table.add_row("api_key_env", status.api_key_env or "")
    for warning in status.warnings:
        table.add_row("warning", warning)
    console.print(table)
    console.print(
        f"chat {status.status} model={status.active_model_profile} "
        f"provider={status.active_provider}",
        markup=False,
    )
    _complete_trace(trace, "chat.status", {"status": status.status})


@usage_app.command("summary")
def usage_summary(root: RootOption = Path(".")) -> None:
    """Show total local token and cost usage."""
    trace = _start_trace(root, "usage.summary")
    summary = UsageStore(root).summary()
    _print_usage_summary_table([summary])
    _complete_trace(trace, "usage.summary", {"total_tokens": summary.total_tokens})


@usage_app.command("today")
def usage_today(root: RootOption = Path(".")) -> None:
    """Show today's local usage summary."""
    trace = _start_trace(root, "usage.today")
    summary = UsageStore(root).today_summary()
    _print_usage_summary_table([summary])
    _complete_trace(trace, "usage.today", {"total_tokens": summary.total_tokens})


@usage_app.command("by-model")
def usage_by_model(root: RootOption = Path(".")) -> None:
    """Show local usage grouped by provider/model/profile."""
    trace = _start_trace(root, "usage.by-model")
    summaries = UsageStore(root).model_summary()
    _print_usage_summary_table(summaries)
    _complete_trace(trace, "usage.by-model", {"rows": len(summaries)})


@usage_app.command("by-agent")
def usage_by_agent(root: RootOption = Path(".")) -> None:
    """Show local usage grouped by agent id."""
    trace = _start_trace(root, "usage.by-agent")
    summaries = UsageStore(root).agent_summary()
    _print_usage_summary_table(summaries)
    _complete_trace(trace, "usage.by-agent", {"rows": len(summaries)})


@usage_app.command("export")
def usage_export(
    format_name: Annotated[
        str,
        typer.Option("--format", help="Export format. Currently only json."),
    ] = "json",
    root: RootOption = Path("."),
) -> None:
    """Export local usage data without prompt bodies."""
    trace = _start_trace(root, "usage.export")
    if format_name != "json":
        _fail_trace(trace, "usage.export", f"Unsupported format: {format_name}")
        console.print("Unsupported usage export format. Use --format json.")
        raise typer.Exit(1)
    payload = UsageStore(root).export_json()
    typer.echo(payload, nl=False)
    _complete_trace(trace, "usage.export", {"format": format_name})


@usage_app.command("reset")
def usage_reset(
    confirm: Annotated[bool, typer.Option("--confirm", help="Confirm usage reset.")] = False,
    root: RootOption = Path("."),
) -> None:
    """Reset local usage event history. Requires --confirm."""
    trace = _start_trace(root, "usage.reset")
    try:
        UsageStore(root).reset(confirm=confirm)
    except ValueError as error:
        _fail_trace(trace, "usage.reset", str(error))
        console.print(str(error))
        raise typer.Exit(1) from error
    console.print("Usage reset")
    _complete_trace(trace, "usage.reset", {"reset": True})


@agents_app.command("list")
def agents_list(root: RootOption = Path(".")) -> None:
    """List local agent runtime records."""
    trace = _start_trace(root, "agents.list")
    agents = AgentRuntimeRegistry(root).list_agents()
    _print_agents_table(agents)
    _complete_trace(trace, "agents.list", {"count": len(agents)})


@agents_app.command("status")
def agents_status(root: RootOption = Path(".")) -> None:
    """Show local active and recent agent runtime status."""
    trace = _start_trace(root, "agents.status")
    agents = AgentRuntimeRegistry(root).list_agents()
    _print_agents_table(agents)
    active_count = sum(
        1 for agent in agents if agent.status.value in {"running", "waiting", "idle"}
    )
    console.print(f"agents active={active_count} total={len(agents)}", markup=False)
    _complete_trace(trace, "agents.status", {"active": active_count, "total": len(agents)})


@agents_app.command("start")
def agents_start(
    name: Annotated[str, typer.Option("--name", help="Agent name.")],
    role: Annotated[str, typer.Option("--role", help="Agent role.")],
    task: Annotated[str, typer.Option("--task", help="Current task summary.")],
    model_profile_name: Annotated[
        str,
        typer.Option("--model", help="Model profile name to associate with this agent."),
    ],
    effort: Annotated[
        str | None,
        typer.Option("--effort", help="Reasoning effort label."),
    ] = None,
    kind: Annotated[
        str,
        typer.Option("--kind", help="Runtime kind: agent or subagent."),
    ] = "agent",
    parent_id: Annotated[
        str | None,
        typer.Option("--parent-id", help="Parent agent id for subagents."),
    ] = None,
    root: RootOption = Path("."),
) -> None:
    """Create a local runtime entry without executing autonomous work."""
    trace = _start_trace(root, "agents.start")
    try:
        agent = AgentRuntimeRegistry(root).start_agent(
            name=name,
            role=role,
            current_task=task,
            model_profile=model_profile_name,
            effort=effort,
            kind=AgentKind(kind),
            parent_id=parent_id,
        )
    except ValueError as error:
        _fail_trace(trace, "agents.start", str(error))
        console.print(str(error))
        raise typer.Exit(1) from error
    trace.log_event(
        TraceEventType.AGENT_STARTED,
        command="agents.start",
        status=agent.status.value,
        payload={
            "agent_id": agent.id,
            "name": agent.name,
            "role": agent.role,
            "kind": agent.kind.value,
            "model_profile": agent.model_profile,
            "parent_id": agent.parent_id or "",
        },
    )
    console.print(f"Started agent {agent.name} ({agent.status.value})", markup=False)
    console.print(f"id={agent.id}", markup=False)
    _complete_trace(trace, "agents.start", {"agent_id": agent.id})


@agents_app.command("stop")
def agents_stop(
    agent_id: Annotated[str, typer.Argument(help="Agent id.")],
    root: RootOption = Path("."),
) -> None:
    """Mark an agent runtime entry as completed."""
    trace = _start_trace(root, "agents.stop")
    try:
        agent = AgentRuntimeRegistry(root).stop_agent(agent_id)
    except KeyError as error:
        _fail_trace(trace, "agents.stop", str(error))
        console.print(str(error))
        raise typer.Exit(1) from error
    trace.log_event(
        TraceEventType.AGENT_STOPPED,
        command="agents.stop",
        status=agent.status.value,
        payload={"agent_id": agent.id, "name": agent.name, "status": agent.status.value},
    )
    console.print(f"Stopped agent {agent.id} status={agent.status.value}", markup=False)
    _complete_trace(trace, "agents.stop", {"agent_id": agent.id, "status": agent.status.value})


@agents_app.command("clear")
def agents_clear(
    confirm: Annotated[bool, typer.Option("--confirm", help="Confirm clearing state.")] = False,
    root: RootOption = Path("."),
) -> None:
    """Clear local agent runtime state. Requires --confirm."""
    trace = _start_trace(root, "agents.clear")
    try:
        AgentRuntimeRegistry(root).clear(confirm=confirm)
    except ValueError as error:
        _fail_trace(trace, "agents.clear", str(error))
        console.print(str(error))
        raise typer.Exit(1) from error
    trace.log_event(
        TraceEventType.AGENT_STATE_CLEARED,
        command="agents.clear",
        status="ok",
        payload={"cleared": True},
    )
    console.print("Cleared agent runtime state")
    _complete_trace(trace, "agents.clear", {"cleared": True})


@eval_app.command("run")
def eval_run(root: RootOption = Path(".")) -> None:
    """Run local AgentOS eval cases and write a JSON result report."""
    trace = _start_trace(root, "eval.run")
    report = EvalRunner(root).run()
    _print_eval_report(report)
    _complete_trace(trace, "eval.run", {"passed": report.passed, **report.summary})
    if not report.passed:
        raise typer.Exit(1)


@refiner_app.command("analyze")
def refiner_analyze(root: RootOption = Path(".")) -> None:
    """Analyze local traces for repeated failures and workflow friction."""
    trace = _start_trace(root, "refiner.analyze")
    analysis = _services(root).refiner.analyze_recent_traces()
    _print_refiner_analysis(analysis)
    _complete_trace(
        trace,
        "refiner.analyze",
        {"finding_count": len(analysis.findings), "events_scanned": analysis.events_scanned},
    )


@refiner_app.command("propose")
def refiner_propose(root: RootOption = Path(".")) -> None:
    """Write a local markdown proposal from recent trace analysis."""
    trace = _start_trace(root, "refiner.propose")
    proposal = _services(root).refiner.create_proposal()
    console.print(f"Proposal written: {proposal.path}")
    _complete_trace(
        trace,
        "refiner.propose",
        {"path": str(proposal.path), "finding_count": proposal.finding_count},
    )


@refiner_app.command("list-proposals")
def refiner_list_proposals(root: RootOption = Path(".")) -> None:
    """List local refiner proposal markdown files."""
    trace = _start_trace(root, "refiner.list-proposals")
    proposals = _services(root).refiner.list_proposals()
    table = Table("Proposal")
    for proposal in proposals:
        table.add_row(str(proposal))
    console.print(table)
    for proposal in proposals:
        console.print(proposal.name, markup=False)
        console.print(str(proposal), markup=False)
    _complete_trace(trace, "refiner.list-proposals", {"count": len(proposals)})


@backup_app.command("create")
def backup_create(root: RootOption = Path(".")) -> None:
    """Create a local zip backup of AgentOS configuration and metadata."""
    trace = _start_trace(root, "backup.create")
    backup = _services(root).backups.create()
    console.print(f"Backup created {backup.id} at {backup.path}")
    _complete_trace(
        trace,
        "backup.create",
        {"backup_id": backup.id, "file_count": backup.file_count},
    )


@backup_app.command("list")
def backup_list(root: RootOption = Path(".")) -> None:
    """List local backups."""
    trace = _start_trace(root, "backup.list")
    backups = _services(root).backups.list()
    table = Table("ID", "Created", "Files", "Path")
    for backup in backups:
        table.add_row(
            backup.id,
            str(backup.metadata.get("created_at", "")),
            str(backup.metadata.get("file_count", 0)),
            str(backup.path),
        )
    console.print(table)
    for backup in backups:
        console.print(f"{backup.id} {backup.path}")
    _complete_trace(trace, "backup.list", {"count": len(backups)})


@backup_app.command("inspect")
def backup_inspect(
    backup_id: Annotated[str, typer.Argument(help="Backup ID.")],
    root: RootOption = Path("."),
) -> None:
    """Inspect backup metadata and included files."""
    trace = _start_trace(root, "backup.inspect")
    try:
        backup = _services(root).backups.inspect(backup_id)
    except FileNotFoundError as error:
        _fail_trace(trace, "backup.inspect", str(error))
        console.print(str(error))
        raise typer.Exit(1) from error
    _print_backup_inspection(backup)
    _complete_trace(
        trace,
        "backup.inspect",
        {"backup_id": backup.id, "file_count": len(backup.files)},
    )


@backup_app.command("restore")
def backup_restore(
    backup_id: Annotated[str, typer.Argument(help="Backup ID.")],
    confirm: Annotated[bool, typer.Option("--confirm", help="Confirm restore.")] = False,
    root: RootOption = Path("."),
) -> None:
    """Restore files from a local backup. Requires --confirm."""
    trace = _start_trace(root, "backup.restore")
    try:
        result = _services(root).backups.restore(backup_id, confirm=confirm)
    except (FileNotFoundError, ValueError) as error:
        _fail_trace(trace, "backup.restore", str(error))
        console.print(str(error))
        raise typer.Exit(1) from error
    console.print(f"Restored {result.file_count} files from {result.backup_id}")
    _complete_trace(
        trace,
        "backup.restore",
        {"backup_id": result.backup_id, "file_count": result.file_count},
    )


@backup_app.command("prune")
def backup_prune(
    keep: Annotated[int, typer.Option("--keep", help="Number of backups to keep.")] = 10,
    root: RootOption = Path("."),
) -> None:
    """Prune old local backups, keeping the most recent backups."""
    trace = _start_trace(root, "backup.prune")
    try:
        removed = _services(root).backups.prune(keep=keep)
    except ValueError as error:
        _fail_trace(trace, "backup.prune", str(error))
        console.print(str(error))
        raise typer.Exit(1) from error
    console.print(f"Pruned {removed} backups; keep={keep}")
    _complete_trace(trace, "backup.prune", {"removed": removed, "keep": keep})


@profile_app.command("init")
def profile_init(root: RootOption = Path(".")) -> None:
    """Create the default AgentOS profile file."""
    trace = _start_trace(root, "profile.init")
    path = _services(root).profiles.create_default()
    _complete_trace(trace, "profile.init", {"path": str(path)})
    console.print(f"Profile file initialized at {path}")


@profile_app.command("list")
def profile_list(root: RootOption = Path(".")) -> None:
    """List available profiles."""
    trace = _start_trace(root, "profile.list")
    profile = _services(root).profiles.load()
    table = Table("Active", "Name", "Default Project", "Memory Project", "Description")
    for name, spec in profile.profiles.items():
        table.add_row(
            "*" if name == profile.active_profile else "",
            name,
            spec.default_project,
            spec.memory_project,
            spec.description,
        )
    console.print(table)
    _complete_trace(trace, "profile.list", {"count": len(profile.profiles)})


@profile_app.command("show")
def profile_show(root: RootOption = Path(".")) -> None:
    """Show the active profile."""
    trace = _start_trace(root, "profile.show")
    profile = _services(root).profiles.load()
    _print_profile(profile)
    _complete_trace(trace, "profile.show", {"active_profile": profile.active_profile})


@profile_app.command("set")
def profile_set(
    profile_name: Annotated[str, typer.Argument(help="Profile name.")],
    root: RootOption = Path("."),
) -> None:
    """Set the active profile."""
    trace = _start_trace(root, "profile.set")
    try:
        profile = _services(root).profiles.set_active(profile_name)
    except KeyError as error:
        _fail_trace(trace, "profile.set", str(error))
        console.print(str(error))
        raise typer.Exit(1) from error
    _complete_trace(trace, "profile.set", {"active_profile": profile.active_profile})
    console.print(f"Active profile set to {profile.active_profile}")


@profile_app.command("validate")
def profile_validate(root: RootOption = Path(".")) -> None:
    """Validate the profile file."""
    trace = _start_trace(root, "profile.validate")
    services = _services(root)
    registry = services.skills.list()
    known_skills = {skill.name for skill in registry.skills}
    validation = services.profiles.validate(known_skills=known_skills)
    for warning in validation.warnings:
        console.print(f"Warning: {warning}")
    for error in validation.errors:
        console.print(error)
    status = "valid" if validation.valid else "invalid"
    console.print(f"Profile file is {status}; warnings: {len(validation.warnings)}")
    _complete_trace(
        trace,
        "profile.validate",
        {"valid": validation.valid, "warning_count": len(validation.warnings)},
    )
    if not validation.valid:
        raise typer.Exit(1)


@memory_app.command("add")
def memory_add(
    content: Annotated[str, typer.Option("--content", help="Memory content.")],
    title: Annotated[str, typer.Option("--title", help="Memory title.")],
    kind: Annotated[str, typer.Option("--kind", help="Memory kind.")] = "note",
    project: Annotated[str | None, typer.Option("--project", help="Project name.")] = None,
    tags: Annotated[list[str] | None, typer.Option("--tag", help="Memory tag.")] = None,
    source: Annotated[str | None, typer.Option("--source", help="Memory source.")] = None,
    confidence: Annotated[
        float,
        typer.Option("--confidence", min=0.0, max=1.0, help="Confidence score."),
    ] = 1.0,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
    root: RootOption = Path("."),
) -> None:
    """Add a technical memory."""
    trace = _start_trace(root, "memory.add")
    resolved_project = _resolve_memory_project(root, project)
    service = _services(root).memory
    memory = service.add_memory(
        project=resolved_project,
        title=title,
        kind=kind,
        content=content,
        tags=tags or [],
        source=source,
        confidence=confidence,
    )
    trace.log_event(
        TraceEventType.MEMORY_ADDED,
        command="memory.add",
        status="ok",
        project=memory.project,
        payload={"memory_id": memory.id, "kind": memory.kind, "title": memory.title},
    )
    _complete_trace(trace, "memory.add")
    if json_output:
        _print_json(memory.model_dump())
    else:
        console.print(f"Added memory {memory.id}: {memory.title}")


@memory_app.command("search")
def memory_search(
    query: Annotated[str, typer.Argument(help="Search query.")],
    project: Annotated[str | None, typer.Option("--project", help="Project filter.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
    root: RootOption = Path("."),
) -> None:
    """Search technical memories."""
    trace = _start_trace(root, "memory.search")
    service = _services(root).memory
    results = service.search_memories(query, project=project)
    trace.log_event(
        TraceEventType.MEMORY_SEARCHED,
        command="memory.search",
        status="ok",
        project=project,
        payload={"query": query, "result_count": len(results)},
    )
    if json_output:
        _print_json({"memories": [item.model_dump() for item in results]})
    else:
        _print_memory_table(results)
    _complete_trace(trace, "memory.search")


@memory_app.command("list")
def memory_list(
    project: Annotated[str | None, typer.Option("--project", help="Project filter.")] = None,
    kind: Annotated[str | None, typer.Option("--kind", help="Kind filter.")] = None,
    limit: Annotated[int | None, typer.Option("--limit", help="Maximum rows to show.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
    root: RootOption = Path("."),
) -> None:
    """List technical memories."""
    trace = _start_trace(root, "memory.list")
    service = _services(root).memory
    results = service.list_memories(project=project, kind=kind, limit=limit)
    if json_output:
        _print_json({"memories": [item.model_dump() for item in results]})
    else:
        _print_memory_table(results)
    _complete_trace(trace, "memory.list", {"count": len(results)})


@memory_app.command("get")
def memory_get(
    memory_id: Annotated[str, typer.Argument(help="Memory ID.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
    root: RootOption = Path("."),
) -> None:
    """Get a technical memory by ID."""
    trace = _start_trace(root, "memory.get")
    service = _services(root).memory
    memory = service.get_memory(memory_id)
    if memory is None:
        _fail_trace(trace, "memory.get", f"Memory not found: {memory_id}")
        _complete_trace(trace, "memory.get", {"found": False})
        console.print(f"Memory not found: {memory_id}")
        raise typer.Exit(1)
    if json_output:
        _print_json(memory.model_dump())
    else:
        _print_memory_detail(memory.model_dump())
    _complete_trace(trace, "memory.get", {"found": True})


@memory_app.command("delete")
def memory_delete(
    memory_id: Annotated[str, typer.Argument(help="Memory ID.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print JSON output.")] = False,
    root: RootOption = Path("."),
) -> None:
    """Delete a technical memory by explicit ID."""
    trace = _start_trace(root, "memory.delete")
    service = _services(root).memory
    deleted = service.delete_memory(memory_id)
    trace.log_event(
        TraceEventType.MEMORY_DELETED,
        command="memory.delete",
        status="ok" if deleted else "failed",
        payload={"memory_id": memory_id, "deleted": deleted},
    )
    _complete_trace(trace, "memory.delete", {"deleted": deleted})
    if json_output:
        _print_json({"id": memory_id, "deleted": deleted})
    elif deleted:
        console.print(f"Deleted memory {memory_id}")
    else:
        console.print(f"Memory not found: {memory_id}")
    if not deleted:
        _fail_trace(trace, "memory.delete", f"Memory not found: {memory_id}")
        raise typer.Exit(1)


@memory_app.command("export")
def memory_export(
    export_format: Annotated[str, typer.Option("--format", help="Export format.")] = "json",
    output: Annotated[Path | None, typer.Option("--output", help="Output file.")] = None,
    root: RootOption = Path("."),
) -> None:
    """Export technical memories."""
    trace = _start_trace(root, "memory.export")
    if export_format != "json":
        raise typer.BadParameter("Only json export is supported.")
    service = _services(root).memory
    if output is None:
        console.print(service.store.export_json_text())
        count = len(service.store.list_memories())
    else:
        count = service.export_memories(output)
        console.print(f"Exported {count} memories to {output}")
    _complete_trace(trace, "memory.export", {"count": count})


@memory_app.command("import")
def memory_import(
    file: Annotated[Path, typer.Argument(help="JSON memory export file.")],
    root: RootOption = Path("."),
) -> None:
    """Import technical memories from a JSON export."""
    trace = _start_trace(root, "memory.import")
    service = _services(root).memory
    count = service.import_memories(file)
    _complete_trace(trace, "memory.import", {"count": count})
    console.print(f"Imported {count} memories from {file}")


@brain_app.command("ingest")
def brain_ingest(
    path: Annotated[Path, typer.Argument(help="Markdown or text document path.")],
    root: RootOption = Path("."),
) -> None:
    """Ingest a Markdown or text document into the strategic brain index."""
    trace = _start_trace(root, "brain.ingest")
    try:
        document = _services(root).strategic_brain.ingest_document(path)
    except (FileNotFoundError, PermissionError, ValueError) as error:
        _fail_trace(trace, "brain.ingest", str(error))
        console.print(str(error))
        raise typer.Exit(1) from error
    _complete_trace(trace, "brain.ingest", {"document_id": document.id})
    console.print(f"Ingested document {document.id}: {document.title}")


@brain_app.command("search")
def brain_search(
    query: Annotated[str, typer.Argument(help="Search query.")],
    limit: Annotated[int, typer.Option("--limit", help="Maximum rows to show.")] = 20,
    root: RootOption = Path("."),
) -> None:
    """Search the strategic brain document index."""
    trace = _start_trace(root, "brain.search")
    results = _services(root).strategic_brain.search_documents(query, limit=limit)
    table = Table("Document ID", "Title", "Chunk", "Path")
    for result in results:
        table.add_row(result.document_id, result.title, _truncate(result.chunk), result.path)
    console.print(table)
    for result in results:
        console.print(f"{result.document_id} {result.title} {result.path}")
    _complete_trace(trace, "brain.search", {"count": len(results)})


@brain_app.command("list")
def brain_list(root: RootOption = Path(".")) -> None:
    """List documents in the strategic brain index."""
    trace = _start_trace(root, "brain.list")
    documents = _services(root).strategic_brain.list_documents()
    table = Table("Document ID", "Title", "Updated", "Path")
    for document in documents:
        table.add_row(document.id, document.title, document.updated_at, document.path)
    console.print(table)
    for document in documents:
        console.print(f"{document.id} {document.title} {document.path}")
    _complete_trace(trace, "brain.list", {"count": len(documents)})


@brain_app.command("show")
def brain_show(
    document_id: Annotated[str, typer.Argument(help="Document ID.")],
    root: RootOption = Path("."),
) -> None:
    """Show a strategic brain document and its chunks."""
    trace = _start_trace(root, "brain.show")
    brain = _services(root).strategic_brain
    document = brain.get_document(document_id)
    if document is None:
        _fail_trace(trace, "brain.show", f"Document not found: {document_id}")
        console.print(f"Document not found: {document_id}")
        raise typer.Exit(1)
    chunks = brain.list_document_chunks(document_id)
    table = Table("Field", "Value")
    table.add_row("id", document.id)
    table.add_row("title", document.title)
    table.add_row("path", document.path)
    table.add_row("content_hash", document.content_hash)
    table.add_row("created_at", document.created_at)
    table.add_row("updated_at", document.updated_at)
    console.print(table)
    for chunk in chunks:
        console.print(f"Chunk {chunk.chunk_index}: {_truncate(chunk.content, 240)}")
    _complete_trace(trace, "brain.show", {"chunk_count": len(chunks)})


@sdd_app.command("new")
def sdd_new(
    change_name: Annotated[str, typer.Argument(help="OpenSpec change name.")],
    root: RootOption = Path("."),
) -> None:
    """Create SDD/OpenSpec artifacts for a change."""
    trace = _start_trace(root, "sdd.new")
    service = _services(root).sdd
    try:
        change = service.create_change(change_name)
    except InvalidSlugError as error:
        _fail_trace(trace, "sdd.new", str(error))
        console.print(str(error))
        raise typer.Exit(1) from error
    trace.log_event(
        TraceEventType.SDD_CREATED,
        command="sdd.new",
        status="ok",
        payload={"change_name": change.name, "path": str(change.path)},
    )
    _complete_trace(trace, "sdd.new")
    console.print(f"Created SDD change at {change.path}")


@sdd_app.command("list")
def sdd_list(root: RootOption = Path(".")) -> None:
    """List SDD/OpenSpec changes."""
    trace = _start_trace(root, "sdd.list")
    changes = _services(root).sdd.list_changes()
    table = Table("Change", "Phase", "Archived", "Path")
    for change in changes:
        table.add_row(change.name, change.phase, str(change.archived), str(change.path))
    console.print(table)
    _complete_trace(trace, "sdd.list", {"count": len(changes)})


@sdd_app.command("status")
def sdd_status(
    change_name: Annotated[str, typer.Argument(help="OpenSpec change name.")],
    root: RootOption = Path("."),
) -> None:
    """Show SDD/OpenSpec change status."""
    trace = _start_trace(root, "sdd.status")
    try:
        change = _services(root).sdd.get_status(change_name)
    except (FileNotFoundError, InvalidSlugError) as error:
        _fail_trace(trace, "sdd.status", str(error))
        console.print(str(error))
        raise typer.Exit(1) from error
    table = Table("Field", "Value")
    table.add_row("name", change.name)
    table.add_row("phase", change.phase)
    table.add_row("archived", str(change.archived))
    table.add_row("path", str(change.path))
    console.print(table)
    _complete_trace(trace, "sdd.status", {"phase": change.phase})


@sdd_app.command("advance")
def sdd_advance(
    change_name: Annotated[str, typer.Argument(help="OpenSpec change name.")],
    phase: Annotated[str, typer.Option("--phase", help="Target workflow phase.")],
    force: Annotated[bool, typer.Option("--force", help="Allow non-linear phase jumps.")] = False,
    root: RootOption = Path("."),
) -> None:
    """Advance an SDD/OpenSpec change to the next phase."""
    trace = _start_trace(root, "sdd.advance")
    try:
        change = _services(root).sdd.advance_change(change_name, phase, force=force)
    except (FileNotFoundError, InvalidPhaseTransitionError, InvalidSlugError) as error:
        _fail_trace(trace, "sdd.advance", str(error))
        console.print(str(error))
        raise typer.Exit(1) from error
    trace.log_event(
        TraceEventType.SDD_PHASE_ADVANCED,
        command="sdd.advance",
        status="ok",
        payload={"change_name": change.name, "phase": change.phase},
    )
    console.print(f"{change.name} advanced to {change.phase}")
    _complete_trace(trace, "sdd.advance", {"phase": change.phase})


@sdd_app.command("archive")
def sdd_archive(
    change_name: Annotated[str, typer.Argument(help="OpenSpec change name.")],
    root: RootOption = Path("."),
) -> None:
    """Mark an SDD/OpenSpec change as archived."""
    trace = _start_trace(root, "sdd.archive")
    try:
        change = _services(root).sdd.archive_change(change_name)
    except (FileNotFoundError, InvalidSlugError) as error:
        _fail_trace(trace, "sdd.archive", str(error))
        console.print(str(error))
        raise typer.Exit(1) from error
    console.print(f"{change.name} archived")
    _complete_trace(trace, "sdd.archive", {"phase": change.phase})


@skills_app.command("scan")
def skills_scan(root: RootOption = Path(".")) -> None:
    """Scan skills/**/SKILL.md and write the local registry."""
    trace = _start_trace(root, "skills.scan")
    registry = _services(root).skills.scan()
    trace.log_event(
        TraceEventType.SKILL_SCAN_COMPLETED,
        command="skills.scan",
        status="ok",
        payload={"count": len(registry.skills), "warning_count": len(registry.warnings)},
    )
    _complete_trace(trace, "skills.scan", {"count": len(registry.skills)})
    for warning in registry.warnings:
        console.print(f"Warning: {warning}")
    console.print(f"Scanned {len(registry.skills)} skills")


@skills_app.command("list")
def skills_list(root: RootOption = Path(".")) -> None:
    """List registered skills without loading full skill content."""
    trace = _start_trace(root, "skills.list")
    registry = _services(root).skills.list()
    table = Table("Name", "Scope", "Valid", "Description", "Path")
    for skill in registry.skills:
        table.add_row(skill.name, skill.scope, str(skill.valid), skill.description, skill.path)
    console.print(table)
    for warning in registry.warnings:
        console.print(f"Warning: {warning}")
    _complete_trace(trace, "skills.list", {"count": len(registry.skills)})


@skills_app.command("show")
def skills_show(
    skill_name: Annotated[str, typer.Argument(help="Skill name.")],
    root: RootOption = Path("."),
) -> None:
    """Show a skill and load its full SKILL.md content."""
    trace = _start_trace(root, "skills.show")
    try:
        skill = _services(root).skills.show(skill_name)
    except KeyError as error:
        _fail_trace(trace, "skills.show", str(error))
        console.print(str(error))
        raise typer.Exit(1) from error
    console.print(f"Name: {skill.name}")
    console.print(f"Scope: {skill.scope}")
    console.print(f"Path: {skill.path}")
    console.print(f"Description: {skill.description}")
    if skill.errors:
        console.print("Errors: " + ", ".join(skill.errors))
    console.print(skill.content)
    _complete_trace(trace, "skills.show", {"skill": skill.name})


@skills_app.command("validate")
def skills_validate(root: RootOption = Path(".")) -> None:
    """Validate registered skill frontmatter."""
    trace = _start_trace(root, "skills.validate")
    validation = _services(root).skills.validate()
    for warning in validation.warnings:
        console.print(f"Warning: {warning}")
    for error in validation.errors:
        console.print(error)
    console.print(
        f"Validated {validation.skill_count} skills; invalid: {validation.invalid_count}"
    )
    _complete_trace(
        trace,
        "skills.validate",
        {"valid": validation.valid, "invalid_count": validation.invalid_count},
    )
    if not validation.valid:
        _fail_trace(trace, "skills.validate", "Invalid skill frontmatter")
        raise typer.Exit(1)


@policies_app.command("check")
def policies_check(
    path: Annotated[str | None, typer.Option("--path", help="Path to check.")] = None,
    command: Annotated[str | None, typer.Option("--command", help="Command to check.")] = None,
    root: RootOption = Path("."),
) -> None:
    """Check a path or command against local policies."""
    trace = _start_trace(root, "policies.check")
    service = _services(root).policies
    results = []
    if path is not None:
        results.append(service.check_path(path))
    if command is not None:
        results.append(service.check_command(command))
    if not results:
        _fail_trace(trace, "policies.check", "Provide --path or --command.")
        raise typer.BadParameter("Provide --path or --command.")
    _print_policy_results(results)
    for result in results:
        trace.log_event(
            TraceEventType.POLICY_CHECKED,
            command="policies.check",
            status=result.severity.value,
            payload={
                "severity": result.severity.value,
                "rule_type": result.rule_type or "",
                "matched_rule": result.matched_rule or "",
                "reason": result.reason,
            },
        )
        if result.severity.value == "block":
            trace.log_event(
                TraceEventType.POLICY_VIOLATION,
                command="policies.check",
                status="block",
                payload={"reason": result.reason, "matched_rule": result.matched_rule or ""},
            )
    _complete_trace(trace, "policies.check", {"allowed": all(result.allowed for result in results)})
    if any(not result.allowed for result in results):
        _fail_trace(trace, "policies.check", "Policy check blocked one or more inputs")
        raise typer.Exit(1)


@policies_app.command("list")
def policies_list(root: RootOption = Path(".")) -> None:
    """List configured policy rules."""
    trace = _start_trace(root, "policies.list")
    rules = _services(root).policies.list_rules()
    table = Table("Type", "Severity", "Pattern", "Source", "Reason")
    for rule in rules:
        table.add_row(rule.rule_type, rule.severity.value, rule.pattern, rule.source, rule.reason)
    console.print(table)
    for rule in rules:
        console.print(
            f"{rule.rule_type} {rule.severity.value} {rule.pattern} {rule.source}: {rule.reason}"
        )
    _complete_trace(trace, "policies.list", {"count": len(rules)})


@policies_app.command("explain")
def policies_explain(root: RootOption = Path(".")) -> None:
    """Explain local policy behavior."""
    trace = _start_trace(root, "policies.explain")
    console.print(_services(root).policies.explain())
    _complete_trace(trace, "policies.explain")


@traces_app.command("list")
def traces_list(root: RootOption = Path(".")) -> None:
    """List available trace dates."""
    trace = _start_trace(root, "traces.list")
    traces = _services(root).traces
    dates = traces.list_dates()
    table = Table("Date", "Events")
    for trace_date in dates:
        table.add_row(trace_date, str(len(traces.read(trace_date))))
    console.print(table)
    _complete_trace(trace, "traces.list", {"count": len(dates)})


@traces_app.command("show")
def traces_show(
    trace_date: Annotated[str, typer.Option("--date", help="Trace date in YYYY-MM-DD.")],
    root: RootOption = Path("."),
) -> None:
    """Show trace events for a date."""
    trace = _start_trace(root, "traces.show")
    for event in _services(root).traces.read(trace_date):
        typer.echo(json.dumps(event.jsonl_payload(), sort_keys=True))
    _complete_trace(trace, "traces.show", {"date": trace_date})


@traces_app.command("tail")
def traces_tail(
    limit: Annotated[int, typer.Option("--limit", help="Number of events to show.")] = 20,
    root: RootOption = Path("."),
) -> None:
    """Show recent trace events."""
    trace = _start_trace(root, "traces.tail")
    for event in _services(root).traces.tail(limit=limit):
        typer.echo(json.dumps(event.jsonl_payload(), sort_keys=True))
    _complete_trace(trace, "traces.tail", {"limit": limit})


@traces_app.command("export")
def traces_export(
    trace_date: Annotated[str | None, typer.Option("--date", help="Trace date.")] = None,
    output: Annotated[Path | None, typer.Option("--output", help="Output JSONL file.")] = None,
    root: RootOption = Path("."),
) -> None:
    """Export trace JSONL."""
    trace = _start_trace(root, "traces.export")
    lines = _services(root).traces.export(trace_date)
    if output is None:
        for line in lines:
            typer.echo(line)
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        console.print(f"Exported {len(lines)} trace events to {output}")
    _complete_trace(trace, "traces.export", {"count": len(lines), "date": trace_date or ""})


app.add_typer(memory_app, name="memory")
app.add_typer(brain_app, name="brain")
app.add_typer(sdd_app, name="sdd")
app.add_typer(skills_app, name="skills")
app.add_typer(policies_app, name="policies")
app.add_typer(traces_app, name="traces")
app.add_typer(profile_app, name="profile")
app.add_typer(ui_app, name="ui")
app.add_typer(mcp_app, name="mcp")
app.add_typer(eval_app, name="eval")
app.add_typer(refiner_app, name="refiner")
app.add_typer(backup_app, name="backup")
models_app.add_typer(models_effort_app, name="effort")
models_app.add_typer(models_route_app, name="route")
app.add_typer(models_app, name="models")
app.add_typer(chat_app, name="chat")
app.add_typer(agents_app, name="agents")
app.add_typer(usage_app, name="usage")


def _print_usage_summary_table(summaries: list[UsageSummary]) -> None:
    table = Table("key", "events", "input_tokens", "output_tokens", "total_tokens", "cost")
    if not summaries:
        table.add_row("none", "0", "0", "0", "0", format_estimated_cost(None))
    for summary in summaries:
        table.add_row(
            summary.key,
            str(summary.event_count),
            str(summary.input_tokens),
            str(summary.output_tokens),
            str(summary.total_tokens),
            format_estimated_cost(summary.estimated_cost_usd),
        )
    console.print(table)


def _services(root: Path) -> ServiceContainer:
    return create_service_container(root)


def _start_trace(root: Path, command: str) -> TraceLogger:
    return _services(root).traces.start(command)


def _complete_trace(
    trace: TraceLogger,
    command: str,
    payload: dict[str, object] | None = None,
) -> None:
    event_payload = {"command": command}
    if payload:
        event_payload.update(payload)
    trace.log_event(
        TraceEventType.COMMAND_COMPLETED,
        command=command,
        status="ok",
        payload=event_payload,
    )


def _fail_trace(trace: TraceLogger, command: str, error: str) -> None:
    trace.log_event(
        TraceEventType.COMMAND_FAILED,
        command=command,
        status="failed",
        error=error,
    )


def _print_memory_table(memories) -> None:
    table = Table("ID", "Project", "Kind", "Title", "Tags", "Confidence")
    for item in memories:
        table.add_row(
            item.id,
            item.project,
            item.kind,
            item.title,
            ", ".join(item.tags),
            f"{item.confidence:.2f}",
        )
    console.print(table)


def _print_memory_detail(memory: dict[str, object]) -> None:
    table = Table("Field", "Value")
    for key, value in memory.items():
        if isinstance(value, list):
            rendered = ", ".join(str(item) for item in value)
        else:
            rendered = "" if value is None else str(value)
        table.add_row(key, rendered)
    console.print(table)


def _print_json(payload: dict[str, object]) -> None:
    typer.echo(json.dumps(payload, indent=2))


def _print_doctor_report(report) -> None:
    console.print("AgentOS Doctor")
    table = Table("Check", "Status", "Detail")
    for check in report.checks:
        table.add_row(check.name, check.status.value, check.detail)
    console.print(table)


def _print_profile(profile: ProjectProfile) -> None:
    active = profile.active
    console.print(f"Active profile: {profile.active_profile}")
    table = Table("Field", "Value")
    table.add_row("name", active.name)
    table.add_row("description", active.description)
    table.add_row("default_project", active.default_project)
    table.add_row("memory_project", active.memory_project)
    table.add_row("preferred_skills", ", ".join(active.preferred_skills))
    table.add_row("sdd_required_for", ", ".join(active.sdd_required_for))
    table.add_row("blocked_paths", ", ".join(active.blocked_paths))
    table.add_row("test_commands", ", ".join(active.test_commands))
    table.add_row("notes", ", ".join(active.notes))
    console.print(table)


def _resolve_memory_project(root: Path, project: str | None) -> str:
    return _services(root).profiles.resolve_memory_project(project)


def _print_policy_results(results) -> None:
    table = Table("Severity", "Rule Type", "Matched Rule", "Reason")
    for result in results:
        table.add_row(
            result.severity.value,
            result.rule_type or "",
            result.matched_rule or "",
            result.reason,
        )
    console.print(table)
    for result in results:
        console.print(
            f"{result.severity.value} {result.rule_type or ''} "
            f"{result.matched_rule or ''}: {result.reason}"
        )


def _print_eval_report(report) -> None:
    table = Table("Case", "Status", "Duration", "Detail")
    for case in report.cases:
        table.add_row(case.name, case.status, f"{case.duration_ms}ms", case.detail)
    console.print(table)
    console.print(
        f"Eval run {report.id}: passed={report.summary['passed']} "
        f"failed={report.summary['failed']} result={report.result_path}"
    )


def _print_agents_table(agents) -> None:
    table = Table(
        "ID",
        "Name",
        "Kind",
        "Status",
        "Role",
        "Model",
        "Effort",
        "Parent",
        "Task",
        "Tokens",
        "Cost",
    )
    for agent in agents:
        table.add_row(
            agent.id,
            agent.name,
            agent.kind.value,
            agent.status.value,
            agent.role,
            agent.model_profile,
            agent.effort,
            agent.parent_id or "",
            _truncate(agent.current_task, 80),
            f"{agent.input_tokens}/{agent.output_tokens}",
            format_estimated_cost(agent.estimated_cost_usd),
        )
    console.print(table)
    for agent in agents:
        console.print(
            f"{agent.id} {agent.name} {agent.kind.value} {agent.status.value} "
            f"role={agent.role} model={agent.model_profile} effort={agent.effort} "
            f"parent={agent.parent_id or ''} task={agent.current_task}",
            markup=False,
        )


def _print_refiner_analysis(analysis: RefinerAnalysis) -> None:
    table = Table("Type", "Severity", "Subject", "Count", "Recommendation")
    for finding in analysis.findings:
        table.add_row(
            finding.finding_type,
            finding.severity,
            finding.subject,
            str(finding.count),
            finding.recommendation,
        )
    console.print(table)
    for finding in analysis.findings:
        console.print(
            f"{finding.finding_type} {finding.severity} {finding.subject} "
            f"count={finding.count}: {finding.detail}"
        )
    if not analysis.findings:
        console.print("No refiner findings in recent traces.")
    console.print(
        f"Refiner analysis: events_scanned={analysis.events_scanned} "
        f"findings={len(analysis.findings)}"
    )


def _print_backup_inspection(backup) -> None:
    table = Table("Field", "Value")
    table.add_row("id", backup.id)
    table.add_row("path", str(backup.path))
    table.add_row("created_at", str(backup.metadata.get("created_at", "")))
    table.add_row("file_count", str(backup.metadata.get("file_count", 0)))
    table.add_row("excluded_count", str(len(backup.excluded)))
    console.print(table)
    files = Table("Included Files")
    for relative_path in backup.files:
        files.add_row(relative_path)
    console.print(files)
    if backup.excluded:
        excluded = Table("Excluded By Policy")
        for relative_path in backup.excluded:
            excluded.add_row(relative_path)
        console.print(excluded)
    for relative_path in backup.files:
        console.print(relative_path)


def _truncate(value: str, limit: int = 120) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."
