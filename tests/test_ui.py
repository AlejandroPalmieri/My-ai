from pathlib import Path

from rich.console import Console

from agentos.agents.registry import AgentRuntimeRegistry
from agentos.agents.schemas import AgentKind
from agentos.config.project import init_project
from agentos.logging.traces import TraceEventType, TraceLogger
from agentos.memory.store import MemoryStore
from agentos.models.config import model_config_path
from agentos.models.usage import record_usage
from agentos.sdd.generator import create_change
from agentos.ui.banner import render_startup_banner
from agentos.ui.dashboard import collect_dashboard_data, render_dashboard
from agentos.ui.layout import render_bottom_bar
from agentos.ui.theme import load_theme
from agentos.usage.store import UsageStore


def _render_text(renderable) -> str:
    console = Console(record=True, width=120, color_system=None)
    console.print(renderable)
    return console.export_text()


def test_zellij_neutral_theme_loads():
    theme = load_theme("zellij-neutral")

    assert theme.name == "zellij-neutral"
    assert theme.palette.background == "#101418"
    assert theme.palette.border_active == "#7AA89F"


def test_banner_renders_runtime_intro(tmp_path):
    init_project(tmp_path)
    data = collect_dashboard_data(tmp_path)

    output = _render_text(render_startup_banner(data.runtime, load_theme("zellij-neutral")))

    assert "AGENTOS" in output
    assert "Personal Agent Operating System" in output
    assert "version" in output
    assert "active profile" in output
    assert "current workspace" in output
    assert "model" in output
    assert "provider" in output
    assert "effort" in output
    assert str(Path(tmp_path).resolve()).split("\\")[0] in output


def test_dashboard_data_assembly(tmp_path):
    init_project(tmp_path)
    MemoryStore(tmp_path).add_memory(
        project="default",
        title="Runtime note",
        kind="note",
        content="Dashboard should not render content.",
        tags=["ui"],
    )
    create_change(tmp_path, "ui-change")
    TraceLogger(tmp_path).log_event(
        TraceEventType.COMMAND_COMPLETED,
        command="memory.add",
        status="ok",
        payload={"title": "Runtime note"},
    )
    TraceLogger(tmp_path).log_event(
        TraceEventType.POLICY_VIOLATION,
        command="policies.check",
        status="block",
        payload={"matched_rule": ".env"},
    )
    skill_dir = tmp_path / ".agents" / "skills" / "dashboard-demo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: dashboard-demo\ndescription: Dashboard demo skill.\n---\n",
        encoding="utf-8",
    )

    data = collect_dashboard_data(tmp_path)

    assert data.runtime.active_profile == "default"
    assert data.runtime.memory_status == "ready"
    assert data.runtime.skill_registry_status in {"ready", "missing"}
    assert data.memory_count == 1
    assert data.recent_memories[0].title == "Runtime note"
    assert data.active_sdd_changes[0].name == "ui-change"
    assert data.registered_skills[0].name == "dashboard-demo"
    assert data.recent_policy_violations[0].matched_rule == "[REDACTED]"
    assert data.recent_traces[-1].event_type == "policy_violation"
    output = _render_text(render_dashboard(data, load_theme("zellij-neutral")))
    assert "Memory count" in output
    assert "Registered skills" in output
    assert "RECENT POLICY VIOLATIONS" in output
    assert "Dashboard should not render content." not in output


def test_plain_dashboard_includes_basic_status_sections(tmp_path):
    init_project(tmp_path)
    MemoryStore(tmp_path).add_memory(
        project="default",
        title="Plain dashboard note",
        kind="note",
        content="Plain mode content should stay hidden.",
        tags=[],
    )

    output = render_dashboard(
        collect_dashboard_data(tmp_path),
        load_theme("zellij-neutral"),
        plain=True,
    )

    assert "Active profile: default" in output
    assert "Memory count: 1" in output
    assert "Registered skills:" in output
    assert "Recent policy violations:" in output
    assert "Latest trace events:" in output
    assert "Agents / Subagents" in output


def test_bottom_bar_includes_model_runtime_usage(tmp_path):
    init_project(tmp_path)
    record_usage(tmp_path, input_tokens=120, output_tokens=80)
    data = collect_dashboard_data(tmp_path)

    output = _render_text(
        render_bottom_bar(data.runtime.model_status, load_theme("zellij-neutral"))
    )

    assert "[q] quit" in output
    assert "model: local-stub" in output
    assert "provider: local" in output
    assert "effort: medium" in output
    assert data.runtime.model_status.context_usage is not None
    assert data.runtime.model_status.context_usage.status == "ok"
    assert "ctx: 2.00%" in output
    assert "tok: 200/10.0k" in output
    assert "i/o/t: 120/80/200" in output
    assert "cost: $0.000000" in output
    assert "session: $0.000000" in output
    assert "today: $0.000000" in output


def test_dashboard_works_without_models_yaml(tmp_path):
    init_project(tmp_path)
    model_config_path(tmp_path).unlink()

    data = collect_dashboard_data(tmp_path)
    output = _render_text(render_dashboard(data, load_theme("zellij-neutral")))

    assert data.runtime.model_status.active_model == "local-stub"
    assert "model: local-stub" in output
    assert "cost: $0.000000" in output


def test_plain_dashboard_includes_model_status(tmp_path):
    init_project(tmp_path)
    record_usage(tmp_path, input_tokens=40, output_tokens=10)

    output = render_dashboard(
        collect_dashboard_data(tmp_path),
        load_theme("zellij-neutral"),
        plain=True,
    )

    assert "Model Runtime" in output
    assert "- model: local-stub" in output
    assert "- provider: local" in output
    assert "- effort: medium" in output
    assert "- context: 0.50%" in output
    assert "- tokens: 50/10.0k" in output
    assert "- cumulative input tokens: 40" in output
    assert "- cumulative output tokens: 10" in output
    assert "- cumulative total tokens: 50" in output
    assert "- cumulative estimated cost: $0.000000" in output


def test_compact_bottom_bar_renders_model_status(tmp_path):
    init_project(tmp_path)
    record_usage(tmp_path, input_tokens=10, output_tokens=5)
    data = collect_dashboard_data(tmp_path)

    output = _render_text(
        render_bottom_bar(
            data.runtime.model_status,
            load_theme("zellij-neutral"),
            compact=True,
        )
    )

    assert "[q] quit" not in output
    assert "model: local-stub" in output
    assert "effort: medium" in output
    assert "ctx: 0.15%" in output
    assert "cost: $0.000000" in output


def test_dashboard_shows_active_agent_in_right_pane(tmp_path):
    init_project(tmp_path)
    agent = AgentRuntimeRegistry(tmp_path).start_agent(
        name="Planner",
        role="planning",
        current_task="Plan dashboard agent pane",
        model_profile="local-stub",
        effort="high",
    )
    UsageStore(tmp_path).record_event(
        session_id="session-1",
        project="default",
        profile="default",
        provider="local",
        model="local-stub",
        effort="high",
        agent_id=agent.id,
        command="chat.once",
        input_tokens=50,
        output_tokens=25,
        estimated_cost_usd=0.075,
        context_used_percent=1.0,
    )

    data = collect_dashboard_data(tmp_path)
    output = _render_text(render_dashboard(data, load_theme("zellij-neutral")))

    assert data.agents[0].name == "Planner"
    assert "Agents / Subagents" in output
    assert "Planner" in output
    assert "planning" in output
    assert "running" in output
    assert "local-stub" in output
    assert "high" in output
    assert "Plan dashboard agent pane" in output
    assert "tok=50/25" in output
    assert "cost=$0.075000" in output


def test_plain_dashboard_shows_subagent_parent_relationship(tmp_path):
    init_project(tmp_path)
    registry = AgentRuntimeRegistry(tmp_path)
    parent = registry.start_agent(
        name="Lead",
        role="coordination",
        current_task="Coordinate runtime registry",
        model_profile="local-stub",
    )
    registry.start_agent(
        name="Researcher",
        role="research",
        current_task="Inspect runtime registry docs",
        model_profile="local-stub",
        kind=AgentKind.SUBAGENT,
        parent_id=parent.id,
    )

    output = render_dashboard(
        collect_dashboard_data(tmp_path),
        load_theme("zellij-neutral"),
        plain=True,
    )

    assert "Agents / Subagents" in output
    assert "- Lead | agent | running | local-stub | high | Coordinate runtime registry" in output
    assert (
        f"- Researcher | subagent | running | local-stub | high | "
        f"Inspect runtime registry docs | parent: {parent.id}"
    ) in output
