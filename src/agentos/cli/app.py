from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from agentos import __version__
from agentos.config.project import init_project
from agentos.logging.traces import TraceLogger
from agentos.services.local import (
    LocalPolicyService,
    LocalSDDService,
    LocalSkillRegistryService,
    LocalTechnicalMemoryService,
)

app = typer.Typer(help="AgentOS Personal local-first agent operating system.")
memory_app = typer.Typer(help="Technical memory commands.")
sdd_app = typer.Typer(help="SDD/OpenSpec artifact commands.")
skills_app = typer.Typer(help="Skill registry commands.")
policies_app = typer.Typer(help="Policy checking commands.")
console = Console()
RootOption = Annotated[Path, typer.Option("--root", help="Project root.")]


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


@memory_app.command("add")
def memory_add(
    content: Annotated[str, typer.Option("--content", help="Memory content.")],
    title: Annotated[str, typer.Option("--title", help="Memory title.")],
    kind: Annotated[str, typer.Option("--kind", help="Memory kind.")] = "note",
    project: Annotated[str, typer.Option("--project", help="Project name.")] = "default",
    tags: Annotated[list[str] | None, typer.Option("--tag", help="Memory tag.")] = None,
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
    )
    trace.log_event("memory_added", {"memory_id": memory.id, "project": memory.project})
    _complete_trace(trace, "memory.add")
    console.print(f"Added memory {memory.id}: {memory.title}")


@memory_app.command("search")
def memory_search(
    query: Annotated[str, typer.Argument(help="Search query.")],
    project: Annotated[str | None, typer.Option("--project", help="Project filter.")] = None,
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
    table = Table("ID", "Project", "Kind", "Title")
    for item in results:
        table.add_row(str(item.id), item.project, item.kind, item.title)
    console.print(table)
    _complete_trace(trace, "memory.search")


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
    change = service.create_change(change_name)
    trace.log_event("sdd_created", {"change_name": change.name, "path": str(change.path)})
    _complete_trace(trace, "sdd.new")
    console.print(f"Created SDD change at {change.path}")


@skills_app.command("scan")
def skills_scan(root: RootOption = Path(".")) -> None:
    """Scan skills/**/SKILL.md and write the local registry."""
    trace = _start_trace(root, "skills.scan")
    registry = LocalSkillRegistryService(root).scan()
    _complete_trace(trace, "skills.scan", {"count": len(registry.skills)})
    console.print(f"Scanned {len(registry.skills)} skills")


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
