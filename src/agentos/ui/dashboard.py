from __future__ import annotations

import json
from pathlib import Path

from rich.console import RenderableType

from agentos import __version__
from agentos.agents.registry import AgentRuntimeRegistry
from agentos.config.profiles import load_project_profile
from agentos.context.estimator import context_usage_from_active_state, estimate_context_usage
from agentos.logging.traces import tail_trace_events
from agentos.memory.store import MemoryStore
from agentos.models.config import inspect_model_status
from agentos.models.routing import effective_effort
from agentos.models.schemas import ModelProviderStatus
from agentos.policies.checker import create_default_policies
from agentos.sdd.generator import list_changes
from agentos.ui.layout import (
    AgentSummary,
    DashboardData,
    MemorySummary,
    ModelStatusSummary,
    PolicyViolationSummary,
    RuntimeInfo,
    SDDChangeSummary,
    SkillSummary,
    TraceSummary,
    render_dashboard_layout,
    render_plain_dashboard,
)
from agentos.ui.theme import Theme
from agentos.usage.store import UsageStore


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
    trace_events = tail_trace_events(root, limit=50)
    traces = [
        TraceSummary(
            event_type=event.event_type.value,
            command=event.command,
            status=event.status,
            timestamp=event.timestamp,
        )
        for event in trace_events[-5:]
    ]
    policy_violations = [
        PolicyViolationSummary(
            command=event.command,
            status=event.status,
            matched_rule=str(event.payload.get("matched_rule") or "unknown"),
            timestamp=event.timestamp,
        )
        for event in trace_events
        if event.event_type.value == "policy_violation"
    ][-5:]

    create_default_policies(root)
    policy_files = sorted((root / "policies").glob("*.yaml"))
    skill_registry_path = agentos_dir / "skill-registry.json"
    registered_skills = _skill_summaries(root, skill_registry_path)
    skill_count = len(registered_skills)
    if not skill_registry_path.exists() and not registered_skills:
        warnings.append("skill registry missing; run agentos skills scan")

    if not policy_files:
        warnings.append("policy files missing")

    usage_store = UsageStore(root)
    model_status = _model_status_summary(root, usage_store)
    warnings.extend(model_status.warnings)
    agents = _agent_summaries(root, usage_store)

    runtime = RuntimeInfo(
        version=__version__,
        active_profile=profile.active_profile,
        workspace=root,
        model_status=model_status,
        memory_status="ready" if memory_store.db_path.exists() else "missing",
        skill_registry_status="ready" if skill_count else "missing",
        policy_status="ready" if policy_files else "missing",
        sdd_status=f"{len(changes)} active",
        memory_db_path=memory_store.db_path,
        skill_registry_path=skill_registry_path,
        policy_files=policy_files,
        warnings=warnings,
    )

    return DashboardData(
        runtime=runtime,
        memory_count=len(memories),
        recent_memories=recent_memories,
        active_sdd_changes=changes,
        registered_skills=registered_skills,
        recent_policy_violations=policy_violations,
        recent_traces=traces,
        agents=agents,
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


def _skill_summaries(root: Path, registry_path: Path) -> list[SkillSummary]:
    if registry_path.exists():
        registry_skills = _registry_skill_summaries(registry_path)
        if registry_skills:
            return registry_skills
    return _discovered_skill_summaries(root)


def _model_status_summary(root: Path, usage_store: UsageStore) -> ModelStatusSummary:
    session_summary = usage_store.session_summary()
    today_summary = usage_store.today_summary()
    try:
        status = inspect_model_status(root)
    except (KeyError, ValueError):
        return ModelStatusSummary(
            active_model_profile="not configured",
            active_provider="not configured",
            active_model="not configured",
            effort="medium",
            context_window_tokens=0,
            context_used_tokens=0,
            context_used_percent=None,
            context_usage=estimate_context_usage(
                model_profile="not configured",
                context_window_tokens=0,
            ),
            cumulative_estimated_cost_usd=None,
            current_session_estimated_cost_usd=session_summary.estimated_cost_usd,
            daily_estimated_cost_usd=today_summary.estimated_cost_usd,
            status="not configured",
            warnings=["model configuration could not be loaded"],
        )
    return _status_to_summary(root, status, usage_store)


def _agent_summaries(root: Path, usage_store: UsageStore) -> list[AgentSummary]:
    usage_by_agent = {summary.agent_id: summary for summary in usage_store.agent_summary()}
    return [
        AgentSummary(
            id=agent.id,
            name=agent.name,
            role=agent.role,
            kind=agent.kind.value,
            status=agent.status.value,
            model_profile=agent.model_profile,
            effort=agent.effort,
            parent_id=agent.parent_id,
            current_task=agent.current_task,
            input_tokens=usage_by_agent.get(agent.id, agent).input_tokens,
            output_tokens=usage_by_agent.get(agent.id, agent).output_tokens,
            estimated_cost_usd=usage_by_agent.get(agent.id, agent).estimated_cost_usd,
        )
        for agent in AgentRuntimeRegistry(root).list_agents()
    ]


def _status_to_summary(
    root: Path,
    status: ModelProviderStatus,
    usage_store: UsageStore,
) -> ModelStatusSummary:
    usage = status.usage
    session_summary = usage_store.session_summary()
    today_summary = usage_store.today_summary()
    return ModelStatusSummary(
        active_model_profile=status.active_model_profile,
        active_provider=status.active_provider,
        active_model=status.active_model,
        effort=effective_effort(root, "default_chat"),
        context_window_tokens=usage.context_window_tokens,
        context_used_tokens=usage.context_used_tokens,
        context_used_percent=usage.context_used_percent,
        context_usage=context_usage_from_active_state(usage),
        cumulative_input_tokens=usage.cumulative_input_tokens,
        cumulative_output_tokens=usage.cumulative_output_tokens,
        cumulative_total_tokens=usage.cumulative_total_tokens,
        cumulative_estimated_cost_usd=usage.cumulative_estimated_cost_usd,
        current_session_estimated_cost_usd=session_summary.estimated_cost_usd,
        daily_estimated_cost_usd=today_summary.estimated_cost_usd,
        status=status.status,
        warnings=status.warnings,
    )


def _registry_skill_summaries(path: Path) -> list[SkillSummary]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    skills = data.get("skills")
    if not isinstance(skills, list):
        return []
    return [
        SkillSummary(
            name=str(skill.get("name") or "unknown"),
            path=str(skill.get("path") or ""),
            valid=bool(skill.get("valid", False)),
        )
        for skill in skills
        if isinstance(skill, dict)
    ]


def _discovered_skill_summaries(root: Path) -> list[SkillSummary]:
    summaries: list[SkillSummary] = []
    for base in [root / "skills", root / ".agents" / "skills"]:
        if not base.exists():
            continue
        for skill_file in sorted(base.glob("**/SKILL.md")):
            metadata = _read_skill_frontmatter(skill_file)
            summaries.append(
                SkillSummary(
                    name=metadata.get("name") or skill_file.parent.name,
                    path=skill_file.relative_to(root).as_posix(),
                    valid=bool(metadata.get("name") and metadata.get("description")),
                )
            )
    return summaries


def _read_skill_frontmatter(path: Path) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        if line_number == 0 and line.strip() != "---":
            return metadata
        if line_number > 0 and line.strip() == "---":
            return metadata
        if line_number > 0 and ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata
