import json
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from agentos import __version__
from agentos.cli.interactive import run_interactive_cli
from agentos.config.project import init_project
from agentos.logging.traces import TraceLogger
from agentos.sdd.generator import InvalidPhaseTransitionError, InvalidSlugError
from agentos.services.local import (
    LocalDoctorService,
    LocalPolicyService,
    LocalSDDService,
    LocalSkillRegistryService,
    LocalTechnicalMemoryService,
)

ROOT_CONTEXT_SETTINGS = {"allow_extra_args": True, "ignore_unknown_options": True}
app = typer.Typer(
    help="AgentOS Personal local-first agent operating system.",
    context_settings=ROOT_CONTEXT_SETTINGS,
)
memory_app = typer.Typer(help="Technical memory commands.")
sdd_app = typer.Typer(help="SDD/OpenSpec artifact commands.")
skills_app = typer.Typer(help="Skill registry commands.")
policies_app = typer.Typer(help="Policy checking commands.")
console = Console()
RootOption = Annotated[Path, typer.Option("--root", help="Project root.")]
TOP_LEVEL_COMMANDS = {"version", "init", "doctor", "memory", "sdd", "skills", "policies"}
TYPER_ROOT_OPTIONS = {"--help", "-h", "--install-completion", "--show-completion"}


@app.callback(invoke_without_command=True, context_settings=ROOT_CONTEXT_SETTINGS)
def root_callback(
    ctx: typer.Context,
    root: RootOption = Path("."),
) -> None:
    """Run the interactive CLI when no subcommand is specified."""
    if ctx.invoked_subcommand is not None:
        return
    trace = _start_trace(root, "interactive")
    run_interactive_cli(root, list(ctx.args), console)
    _complete_trace(trace, "interactive", {"forwarded_arg_count": len(ctx.args)})


def main(args: list[str] | None = None) -> None:
    """Console-script entrypoint that forwards no-subcommand invocations."""
    cli_args = list(sys.argv[1:] if args is None else args)
    if _should_run_interactive(cli_args):
        root, forwarded_args = _extract_interactive_args(cli_args)
        trace = _start_trace(root, "interactive")
        run_interactive_cli(root, forwarded_args, console)
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


def _extract_interactive_args(args: list[str]) -> tuple[Path, list[str]]:
    root = Path(".")
    forwarded_args: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--root" and index + 1 < len(args):
            root = Path(args[index + 1])
            index += 2
        elif arg.startswith("--root="):
            root = Path(arg.split("=", 1)[1])
            index += 1
        else:
            forwarded_args.append(arg)
            index += 1
    return root, forwarded_args


def _first_non_root_option_index(args: list[str]) -> int:
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--root":
            index += 2
        elif arg.startswith("--root="):
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
    report = LocalDoctorService(root).run()
    _print_doctor_report(report)
    _complete_trace(trace, "doctor", {"healthy": report.healthy})
    if not report.healthy:
        raise typer.Exit(1)


@memory_app.command("add")
def memory_add(
    content: Annotated[str, typer.Option("--content", help="Memory content.")],
    title: Annotated[str, typer.Option("--title", help="Memory title.")],
    kind: Annotated[str, typer.Option("--kind", help="Memory kind.")] = "note",
    project: Annotated[str, typer.Option("--project", help="Project name.")] = "default",
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
    service = LocalTechnicalMemoryService(root)
    memory = service.add_memory(
        project=project,
        title=title,
        kind=kind,
        content=content,
        tags=tags or [],
        source=source,
        confidence=confidence,
    )
    trace.log_event("memory_added", {"memory_id": memory.id, "project": memory.project})
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
    service = LocalTechnicalMemoryService(root)
    results = service.search_memories(query, project=project)
    trace.log_event(
        "search_performed",
        {"query": query, "project": project or "", "result_count": len(results)},
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
    service = LocalTechnicalMemoryService(root)
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
    service = LocalTechnicalMemoryService(root)
    memory = service.get_memory(memory_id)
    if memory is None:
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
    service = LocalTechnicalMemoryService(root)
    deleted = service.delete_memory(memory_id)
    _complete_trace(trace, "memory.delete", {"deleted": deleted})
    if json_output:
        _print_json({"id": memory_id, "deleted": deleted})
    elif deleted:
        console.print(f"Deleted memory {memory_id}")
    else:
        console.print(f"Memory not found: {memory_id}")
    if not deleted:
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
    service = LocalTechnicalMemoryService(root)
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
    service = LocalTechnicalMemoryService(root)
    count = service.import_memories(file)
    _complete_trace(trace, "memory.import", {"count": count})
    console.print(f"Imported {count} memories from {file}")


@sdd_app.command("new")
def sdd_new(
    change_name: Annotated[str, typer.Argument(help="OpenSpec change name.")],
    root: RootOption = Path("."),
) -> None:
    """Create SDD/OpenSpec artifacts for a change."""
    trace = _start_trace(root, "sdd.new")
    service = LocalSDDService(root)
    try:
        change = service.create_change(change_name)
    except InvalidSlugError as error:
        console.print(str(error))
        raise typer.Exit(1) from error
    trace.log_event("sdd_created", {"change_name": change.name, "path": str(change.path)})
    _complete_trace(trace, "sdd.new")
    console.print(f"Created SDD change at {change.path}")


@sdd_app.command("list")
def sdd_list(root: RootOption = Path(".")) -> None:
    """List SDD/OpenSpec changes."""
    trace = _start_trace(root, "sdd.list")
    changes = LocalSDDService(root).list_changes()
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
        change = LocalSDDService(root).get_status(change_name)
    except (FileNotFoundError, InvalidSlugError) as error:
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
        change = LocalSDDService(root).advance_change(change_name, phase, force=force)
    except (FileNotFoundError, InvalidPhaseTransitionError, InvalidSlugError) as error:
        console.print(str(error))
        raise typer.Exit(1) from error
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
        change = LocalSDDService(root).archive_change(change_name)
    except (FileNotFoundError, InvalidSlugError) as error:
        console.print(str(error))
        raise typer.Exit(1) from error
    console.print(f"{change.name} archived")
    _complete_trace(trace, "sdd.archive", {"phase": change.phase})


@skills_app.command("scan")
def skills_scan(root: RootOption = Path(".")) -> None:
    """Scan skills/**/SKILL.md and write the local registry."""
    trace = _start_trace(root, "skills.scan")
    registry = LocalSkillRegistryService(root).scan()
    _complete_trace(trace, "skills.scan", {"count": len(registry.skills)})
    for warning in registry.warnings:
        console.print(f"Warning: {warning}")
    console.print(f"Scanned {len(registry.skills)} skills")


@skills_app.command("list")
def skills_list(root: RootOption = Path(".")) -> None:
    """List registered skills without loading full skill content."""
    trace = _start_trace(root, "skills.list")
    registry = LocalSkillRegistryService(root).list()
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
        skill = LocalSkillRegistryService(root).show(skill_name)
    except KeyError as error:
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
    validation = LocalSkillRegistryService(root).validate()
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
        raise typer.Exit(1)


@policies_app.command("check")
def policies_check(
    path: Annotated[str | None, typer.Option("--path", help="Path to check.")] = None,
    command: Annotated[str | None, typer.Option("--command", help="Command to check.")] = None,
    root: RootOption = Path("."),
) -> None:
    """Check a path or command against local policies."""
    trace = _start_trace(root, "policies.check")
    service = LocalPolicyService(root)
    results = []
    if path is not None:
        results.append(service.check_path(path))
    if command is not None:
        results.append(service.check_command(command))
    if not results:
        raise typer.BadParameter("Provide --path or --command.")
    for result in results:
        console.print(result.reason)
        if not result.allowed:
            trace.log_event("policy_violation", {"reason": result.reason})
    _complete_trace(trace, "policies.check", {"allowed": all(result.allowed for result in results)})
    if any(not result.allowed for result in results):
        raise typer.Exit(1)


app.add_typer(memory_app, name="memory")
app.add_typer(sdd_app, name="sdd")
app.add_typer(skills_app, name="skills")
app.add_typer(policies_app, name="policies")


def _start_trace(root: Path, command: str) -> TraceLogger:
    trace = TraceLogger(root)
    trace.log_event("command_started", {"command": command})
    return trace


def _complete_trace(
    trace: TraceLogger,
    command: str,
    payload: dict[str, object] | None = None,
) -> None:
    event_payload = {"command": command}
    if payload:
        event_payload.update(payload)
    trace.log_event("command_completed", event_payload)


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
