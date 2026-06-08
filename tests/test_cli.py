import json
from datetime import UTC, datetime

from typer.testing import CliRunner

from agentos.cli.app import app

runner = CliRunner()


def test_version_command():
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "AgentOS Personal" in result.output


def test_doctor_command_reports_environment(tmp_path):
    venv_agentos = tmp_path / ".venv" / "Scripts" / "agentos.exe"
    venv_agentos.parent.mkdir(parents=True)
    venv_agentos.write_text("", encoding="utf-8")
    result = runner.invoke(app, ["doctor", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "AgentOS Doctor" in result.output
    assert "python" in result.output
    assert "sqlite" in result.output


def test_profile_cli_init_list_show_set_validate(tmp_path):
    init_result = runner.invoke(app, ["profile", "init", "--root", str(tmp_path)])
    list_result = runner.invoke(app, ["profile", "list", "--root", str(tmp_path)])
    show_result = runner.invoke(app, ["profile", "show", "--root", str(tmp_path)])
    set_result = runner.invoke(app, ["profile", "set", "data-science", "--root", str(tmp_path)])
    validate_result = runner.invoke(app, ["profile", "validate", "--root", str(tmp_path)])

    assert init_result.exit_code == 0
    assert list_result.exit_code == 0
    assert "godot" in list_result.output
    assert "default" in list_result.output
    assert show_result.exit_code == 0
    assert "Active profile" in show_result.output
    assert set_result.exit_code == 0
    assert "data-science" in set_result.output
    assert validate_result.exit_code == 0
    assert "valid" in validate_result.output


def test_no_dashboard_flag_shows_banner_without_dashboard(tmp_path):
    result = runner.invoke(
        app,
        ["--no-dashboard", "--root", str(tmp_path)],
        input="exit\n",
    )

    assert result.exit_code == 0
    assert "AGENTOS" in result.output
    assert "Personal Agent Operating System" in result.output
    assert "Workspace Overview" not in result.output


def test_ui_themes_cli_lists_zellij_neutral(tmp_path):
    result = runner.invoke(app, ["ui", "themes", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "zellij-neutral" in result.output


def test_init_command_creates_local_structure(tmp_path):
    result = runner.invoke(app, ["init", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert (tmp_path / ".agentos").exists()
    assert (tmp_path / ".agentos" / "brain").exists()
    assert (tmp_path / ".agentos" / "config.yaml").exists()
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
    assert {"command_started", "memory_added", "memory_searched", "command_completed"}.issubset(
        _trace_events(tmp_path)
    )


def test_memory_add_uses_active_profile_when_project_omitted(tmp_path):
    runner.invoke(app, ["profile", "init", "--root", str(tmp_path)])
    runner.invoke(app, ["profile", "set", "usmle", "--root", str(tmp_path)])

    add_result = runner.invoke(
        app,
        [
            "memory",
            "add",
            "--root",
            str(tmp_path),
            "--title",
            "Profile memory",
            "--content",
            "Use active profile memory project.",
            "--json",
        ],
    )
    payload = json.loads(add_result.output)

    assert add_result.exit_code == 0
    assert payload["project"] == "usmle"


def test_memory_list_get_delete_and_json_commands(tmp_path):
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
            "JSON memory",
            "--kind",
            "note",
            "--content",
            "Readable and structured",
            "--json",
        ],
    )
    payload = json.loads(add_result.output)
    memory_id = payload["id"]

    list_result = runner.invoke(app, ["memory", "list", "--root", str(tmp_path), "--json"])
    get_result = runner.invoke(app, ["memory", "get", memory_id, "--root", str(tmp_path), "--json"])
    delete_result = runner.invoke(app, ["memory", "delete", memory_id, "--root", str(tmp_path)])
    missing_result = runner.invoke(app, ["memory", "get", memory_id, "--root", str(tmp_path)])

    assert add_result.exit_code == 0
    assert list_result.exit_code == 0
    assert get_result.exit_code == 0
    assert delete_result.exit_code == 0
    assert missing_result.exit_code == 1
    assert json.loads(list_result.output)["memories"][0]["id"] == memory_id
    assert json.loads(get_result.output)["title"] == "JSON memory"
    assert "Deleted memory" in delete_result.output


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


def test_brain_ingest_search_list_show_commands(tmp_path):
    source = tmp_path / "strategy.md"
    source.write_text(
        "# Strategy Notes\n\nAgentOS strategic brain indexes local documents.",
        encoding="utf-8",
    )

    ingest_result = runner.invoke(app, ["brain", "ingest", str(source), "--root", str(tmp_path)])
    list_result = runner.invoke(app, ["brain", "list", "--root", str(tmp_path)])
    search_result = runner.invoke(app, ["brain", "search", "indexes", "--root", str(tmp_path)])

    assert ingest_result.exit_code == 0
    assert "Strategy Notes" in ingest_result.output
    assert list_result.exit_code == 0
    assert "Strategy Notes" in list_result.output
    assert search_result.exit_code == 0
    assert "Strategy Notes" in search_result.output

    document_id = ingest_result.output.split("Ingested document ", 1)[1].split(":", 1)[0]
    show_result = runner.invoke(app, ["brain", "show", document_id, "--root", str(tmp_path)])

    assert show_result.exit_code == 0
    assert "Strategy Notes" in show_result.output


def test_sdd_skills_and_policies_commands(tmp_path):
    skill_dir = tmp_path / "skills" / "demo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: demo\ndescription: Demo skill.\n---\n",
        encoding="utf-8",
    )

    sdd_result = runner.invoke(app, ["sdd", "new", "demo-change", "--root", str(tmp_path)])
    status_result = runner.invoke(app, ["sdd", "status", "demo-change", "--root", str(tmp_path)])
    advance_result = runner.invoke(
        app,
        ["sdd", "advance", "demo-change", "--phase", "explore", "--root", str(tmp_path)],
    )
    list_result = runner.invoke(app, ["sdd", "list", "--root", str(tmp_path)])
    archive_result = runner.invoke(app, ["sdd", "archive", "demo-change", "--root", str(tmp_path)])
    skills_result = runner.invoke(app, ["skills", "scan", "--root", str(tmp_path)])
    skills_list_result = runner.invoke(app, ["skills", "list", "--root", str(tmp_path)])
    skills_show_result = runner.invoke(app, ["skills", "show", "demo", "--root", str(tmp_path)])
    skills_validate_result = runner.invoke(app, ["skills", "validate", "--root", str(tmp_path)])
    policies_result = runner.invoke(
        app,
        ["policies", "check", "--root", str(tmp_path), "--path", ".env"],
    )

    assert sdd_result.exit_code == 0
    assert status_result.exit_code == 0
    assert advance_result.exit_code == 0
    assert list_result.exit_code == 0
    assert archive_result.exit_code == 0
    assert "init" in status_result.output
    assert "explore" in advance_result.output
    assert "demo-change" in list_result.output
    assert skills_result.exit_code == 0
    assert skills_list_result.exit_code == 0
    assert skills_show_result.exit_code == 0
    assert skills_validate_result.exit_code == 0
    assert "demo" in skills_list_result.output
    assert "Demo skill" in skills_show_result.output
    assert policies_result.exit_code == 1
    assert (tmp_path / "openspec" / "changes" / "demo-change" / "proposal.md").exists()
    assert (tmp_path / "openspec" / "changes" / "demo-change" / "metadata.json").exists()
    assert (tmp_path / ".agentos" / "skill-registry.json").exists()
    assert {"sdd_created", "policy_violation"}.issubset(_trace_events(tmp_path))


def test_sdd_invalid_slug_cli_rejected(tmp_path):
    result = runner.invoke(app, ["sdd", "new", "Bad Slug!", "--root", str(tmp_path)])

    assert result.exit_code != 0
    assert "Invalid change name" in result.output


def test_skills_validate_cli_reports_invalid_skill(tmp_path):
    skill_dir = tmp_path / ".agents" / "skills" / "invalid"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: invalid\n---\n", encoding="utf-8")

    result = runner.invoke(app, ["skills", "validate", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "missing description" in result.output


def test_policies_check_cli_prints_severity_and_matched_rule(tmp_path):
    result = runner.invoke(
        app,
        [
            "policies",
            "check",
            "--root",
            str(tmp_path),
            "--command",
            "Remove-Item -Path .\\build -Recurse -Force",
        ],
    )

    assert result.exit_code == 1
    assert "block" in result.output
    assert "Remove-Item -Recurse -Force" in result.output


def test_policies_list_and_explain_cli(tmp_path):
    list_result = runner.invoke(app, ["policies", "list", "--root", str(tmp_path)])
    explain_result = runner.invoke(app, ["policies", "explain", "--root", str(tmp_path)])

    assert list_result.exit_code == 0
    assert "sensitive_path" in list_result.output
    assert "destructive_command" in list_result.output
    assert explain_result.exit_code == 0
    assert "Sensitive paths are blocked" in explain_result.output


def test_traces_cli_list_show_tail_and_export(tmp_path):
    runner.invoke(app, ["doctor", "--root", str(tmp_path)])
    trace_date = datetime.now(UTC).date().isoformat()

    list_result = runner.invoke(app, ["traces", "list", "--root", str(tmp_path)])
    show_result = runner.invoke(
        app,
        ["traces", "show", "--date", trace_date, "--root", str(tmp_path)],
    )
    tail_result = runner.invoke(app, ["traces", "tail", "--root", str(tmp_path)])
    export_result = runner.invoke(app, ["traces", "export", "--root", str(tmp_path)])

    assert list_result.exit_code == 0
    assert trace_date in list_result.output
    assert show_result.exit_code == 0
    assert '"event_type": "command_started"' in show_result.output
    assert tail_result.exit_code == 0
    assert "command_completed" in tail_result.output
    assert export_result.exit_code == 0
    assert all(json.loads(line) for line in export_result.output.splitlines() if line.strip())


def _trace_events(root):
    trace_path = root / ".agentos" / "traces" / f"{datetime.now(UTC).date()}.jsonl"
    return {
        json.loads(line)["event"]
        for line in trace_path.read_text(encoding="utf-8").splitlines()
        if line
    }
