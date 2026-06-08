from pathlib import Path

from rich.console import Console

from agentos.config.project import init_project
from agentos.logging.traces import TraceEventType, TraceLogger
from agentos.memory.store import MemoryStore
from agentos.sdd.generator import create_change
from agentos.ui.banner import render_startup_banner
from agentos.ui.dashboard import collect_dashboard_data, render_dashboard
from agentos.ui.theme import load_theme


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
    assert str(Path(tmp_path).resolve()) in output


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

    data = collect_dashboard_data(tmp_path)

    assert data.runtime.active_profile == "default"
    assert data.runtime.memory_status == "ready"
    assert data.runtime.skill_registry_status in {"ready", "missing"}
    assert data.recent_memories[0].title == "Runtime note"
    assert data.active_sdd_changes[0].name == "ui-change"
    assert data.recent_traces[0].event_type == "command_completed"
    assert "Dashboard should not render content." not in _render_text(
        render_dashboard(data, load_theme("zellij-neutral"))
    )
