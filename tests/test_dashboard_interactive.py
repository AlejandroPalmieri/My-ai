from agentos.config.project import init_project
from agentos.memory.store import MemoryStore
from agentos.ui.interactive import DashboardController


def test_dashboard_controller_switches_focus_and_quits(tmp_path):
    init_project(tmp_path)
    controller = DashboardController(tmp_path)

    assert controller.focus == "overview"

    sdd_result = controller.handle_key("s")
    assert controller.focus == "sdd"

    next_result = controller.handle_key("tab")
    quit_result = controller.handle_key("q")

    assert sdd_result.message == "Focused SDD"
    assert next_result.message.startswith("Focused ")
    assert quit_result.should_exit is True


def test_dashboard_controller_refreshes_data(tmp_path):
    init_project(tmp_path)
    controller = DashboardController(tmp_path)
    assert controller.data.memory_count == 0

    MemoryStore(tmp_path).add_memory(
        project="default",
        title="Refresh note",
        kind="note",
        content="Refreshed data.",
        tags=[],
    )
    result = controller.handle_key("r")

    assert result.message == "Dashboard refreshed"
    assert controller.data.memory_count == 1


def test_dashboard_controller_runs_safe_local_actions(tmp_path):
    init_project(tmp_path)
    skill_dir = tmp_path / ".agents" / "skills" / "demo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: demo\ndescription: Demo skill.\n---\n",
        encoding="utf-8",
    )
    controller = DashboardController(tmp_path)

    backup_result = controller.handle_key("b")
    skills_result = controller.handle_key("k")
    eval_result = controller.handle_key("e")

    assert backup_result.message.startswith("Backup created ")
    assert (tmp_path / ".agentos" / "backups").exists()
    assert skills_result.message == "Scanned 1 skills"
    assert (tmp_path / ".agentos" / "skill-registry.json").exists()
    assert eval_result.message.startswith("Eval run passed")
    assert (tmp_path / ".agentos" / "evals" / "results").exists()


def test_dashboard_controller_keeps_policy_values_redacted(tmp_path):
    init_project(tmp_path)
    controller = DashboardController(tmp_path)

    result = controller.handle_key("u")

    assert "cannot reveal sensitive redacted values" in result.message
