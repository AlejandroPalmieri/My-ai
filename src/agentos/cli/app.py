import json
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from agentos import __version__
from agentos.cli.interactive import run_interactive_cli
from agentos.config.profiles import ProjectProfile
from agentos.config.project import init_project
from agentos.config.settings import set_banner_visibility, set_theme
from agentos.logging.traces import (
    TraceEventType,
    TraceLogger,
)
from agentos.mcp.server import serve_stdio
from agentos.sdd.generator import InvalidPhaseTransitionError, InvalidSlugError
from agentos.services.container import ServiceContainer, create_service_container
from agentos.ui.banner import render_startup_banner
from agentos.ui.dashboard import collect_dashboard_data, render_dashboard
from agentos.ui.theme import list_themes, load_theme

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
    root: RootOption = Path("."),
) -> None:
    """Render the read-only terminal dashboard."""
    trace = _start_trace(root, "dashboard")
    try:
        ui_theme = load_theme(theme)
    except KeyError as error:
        _fail_trace(trace, "dashboard", str(error))
        console.print(str(error))
        raise typer.Exit(1) from error
    data = collect_dashboard_data(root)
    compact = console.width < 100
    console.print(render_dashboard(data, ui_theme, compact=compact, plain=plain))
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


def _truncate(value: str, limit: int = 120) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."
