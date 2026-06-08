from __future__ import annotations

import json
from pathlib import Path

from rich.console import RenderableType

from agentos import __version__
from agentos.config.profiles import load_project_profile
from agentos.logging.traces import tail_trace_events
from agentos.memory.store import MemoryStore
from agentos.policies.checker import create_default_policies
from agentos.sdd.generator import list_changes
from agentos.ui.layout import (
    DashboardData,
    MemorySummary,
    RuntimeInfo,
    SDDChangeSummary,
    TraceSummary,
    render_dashboard_layout,
    render_plain_dashboard,
)
from agentos.ui.theme import Theme


def collect_dashboard_data(root: Path) -> DashboardData:
    root = root.resolve()
    agentos_dir = root / ".agentos"
    warnings: list[str] = []

    profile = load_project_profile(root)
    memory_store = MemoryStore(root)
    memories = memory_store.list_memories()
    recent_memories = [
        MemorySummary(
            id=memory.id,
            project=memory.project,
            title=memory.title,
            kind=memory.kind,
            updated_at=memory.updated_at,
        )
        for memory in reversed(memories[-5:])
    ]

    changes = [
        SDDChangeSummary(name=change.name, phase=change.phase, archived=change.archived)
        for change in list_changes(root)
        if not change.archived
    ][:5]
    traces = [
        TraceSummary(
            event_type=event.event_type.value,
            command=event.command,
            status=event.status,
            timestamp=event.timestamp,
        )
        for event in tail_trace_events(root, limit=5)
    ]

    create_default_policies(root)
    policy_files = sorted((root / "policies").glob("*.yaml"))
    skill_registry_path = agentos_dir / "skill-registry.json"
    skill_count = _skill_count(skill_registry_path)
    if skill_count is None:
        warnings.append("skill registry missing; run agentos skills scan")
    if not policy_files:
        warnings.append("policy files missing")

    runtime = RuntimeInfo(
        version=__version__,
        active_profile=profile.active_profile,
        workspace=root,
        memory_status="ready" if memory_store.db_path.exists() else "missing",
        skill_registry_status="ready" if skill_count is not None else "missing",
        policy_status="ready" if policy_files else "missing",
        sdd_status=f"{len(changes)} active",
        memory_db_path=memory_store.db_path,
        skill_registry_path=skill_registry_path,
        policy_files=policy_files,
        warnings=warnings,
    )
    return DashboardData(
        runtime=runtime,
        recent_memories=recent_memories,
        active_sdd_changes=changes,
        recent_traces=traces,
    )


def render_dashboard(
    data: DashboardData,
    theme: Theme,
    *,
    compact: bool = False,
    plain: bool = False,
) -> RenderableType | str:
    if plain:
        return render_plain_dashboard(data)
    return render_dashboard_layout(data, theme, compact=compact)


def _skill_count(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    skills = data.get("skills")
    return len(skills) if isinstance(skills, list) else None
