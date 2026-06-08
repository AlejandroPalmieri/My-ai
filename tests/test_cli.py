import json
from datetime import UTC, datetime

from typer.testing import CliRunner

from agentos.cli.app import app

runner = CliRunner()


def test_version_command():
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "AgentOS Personal" in result.output


def test_init_command_creates_local_structure(tmp_path):
    result = runner.invoke(app, ["init", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert (tmp_path / ".agentos").exists()
    assert (tmp_path / ".agentos" / "profile.yaml").exists()
    assert (tmp_path / "policies" / "sensitive_paths.yaml").exists()
    assert (tmp_path / "policies" / "destructive_commands.yaml").exists()


def test_memory_add_and_search_commands(tmp_path):
    add_result = runner.invoke(
        app,
        [
            "memory",
            "add",
            "--root",
            str(tmp_path),
            "--project",
            "demo",
            "--title",
            "CLI memory",
            "--kind",
            "note",
            "--content",
            "Searchable CLI content",
            "--tag",
            "cli",
        ],
    )
    search_result = runner.invoke(
        app,
        ["memory", "search", "Searchable", "--root", str(tmp_path), "--project", "demo"],
    )

    assert add_result.exit_code == 0
    assert search_result.exit_code == 0
    assert "CLI memory" in search_result.output
    assert {"command_started", "memory_added", "search_performed", "command_completed"}.issubset(
        _trace_events(tmp_path)
    )


def test_memory_export_and_import_commands(tmp_path):
    export_path = tmp_path / "export.json"
    runner.invoke(
        app,
        [
            "memory",
            "add",
            "--root",
            str(tmp_path),
            "--project",
            "demo",
            "--title",
            "Exported",
            "--kind",
            "note",
            "--content",
            "Imported later",
        ],
    )

    export_result = runner.invoke(
        app,
        [
            "memory",
            "export",
            "--root",
            str(tmp_path),
            "--format",
            "json",
            "--output",
            str(export_path),
        ],
    )
    import_result = runner.invoke(
        app,
        ["memory", "import", str(export_path), "--root", str(tmp_path / "imported")],
    )
    search_result = runner.invoke(
        app,
        ["memory", "search", "Imported", "--root", str(tmp_path / "imported")],
    )

    assert export_result.exit_code == 0
    assert import_result.exit_code == 0
    assert search_result.exit_code == 0
    assert "Exported" in search_result.output


def test_sdd_skills_and_policies_commands(tmp_path):
    skill_dir = tmp_path / "skills" / "demo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: demo\ndescription: Demo skill.\n---\n",
        encoding="utf-8",
    )

    sdd_result = runner.invoke(app, ["sdd", "new", "demo-change", "--root", str(tmp_path)])
    skills_result = runner.invoke(app, ["skills", "scan", "--root", str(tmp_path)])
    policies_result = runner.invoke(
        app,
        ["policies", "check", "--root", str(tmp_path), "--path", ".env"],
    )

    assert sdd_result.exit_code == 0
    assert skills_result.exit_code == 0
    assert policies_result.exit_code == 1
    assert (tmp_path / "openspec" / "changes" / "demo-change" / "proposal.md").exists()
    assert (tmp_path / ".agentos" / "skill-registry.json").exists()
    assert {"sdd_created", "policy_violation"}.issubset(_trace_events(tmp_path))


def _trace_events(root):
    trace_path = root / ".agentos" / "traces" / f"{datetime.now(UTC).date()}.jsonl"
    return {
        json.loads(line)["event"]
        for line in trace_path.read_text(encoding="utf-8").splitlines()
        if line
    }
