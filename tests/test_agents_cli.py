from datetime import UTC, datetime

from typer.testing import CliRunner

from agentos.cli.app import app

runner = CliRunner()


def test_agents_cli_start_list_status_stop(tmp_path):
    start = runner.invoke(
        app,
        [
            "agents",
            "start",
            "--name",
            "Planner",
            "--role",
            "planning",
            "--task",
            "Plan runtime registry",
            "--model",
            "local-stub",
            "--root",
            str(tmp_path),
        ],
    )
    list_result = runner.invoke(app, ["agents", "list", "--root", str(tmp_path)])
    status = runner.invoke(app, ["agents", "status", "--root", str(tmp_path)])
    agent_id = _agent_id_from_output(start.output)
    stop = runner.invoke(app, ["agents", "stop", agent_id, "--root", str(tmp_path)])

    assert start.exit_code == 0
    assert "Started agent" in start.output
    assert list_result.exit_code == 0
    assert "Planner" in list_result.output
    assert "Plan runtime registry" in list_result.output
    assert status.exit_code == 0
    assert "running" in status.output
    assert stop.exit_code == 0
    assert "Stopped agent" in stop.output


def test_agents_cli_clear_requires_confirm(tmp_path):
    runner.invoke(
        app,
        [
            "agents",
            "start",
            "--name",
            "Temp",
            "--role",
            "testing",
            "--task",
            "Clear guard",
            "--model",
            "local-stub",
            "--root",
            str(tmp_path),
        ],
    )

    rejected = runner.invoke(app, ["agents", "clear", "--root", str(tmp_path)])
    accepted = runner.invoke(
        app,
        ["agents", "clear", "--confirm", "--root", str(tmp_path)],
    )

    assert rejected.exit_code == 1
    assert "--confirm" in rejected.output
    assert accepted.exit_code == 0
    assert "Cleared agent runtime state" in accepted.output


def test_agents_cli_subagent_parent_relationship(tmp_path):
    parent = runner.invoke(
        app,
        [
            "agents",
            "start",
            "--name",
            "Lead",
            "--role",
            "coordination",
            "--task",
            "Coordinate subtask",
            "--model",
            "local-stub",
            "--root",
            str(tmp_path),
        ],
    )
    parent_id = _agent_id_from_output(parent.output)
    subagent = runner.invoke(
        app,
        [
            "agents",
            "start",
            "--name",
            "Researcher",
            "--role",
            "research",
            "--task",
            "Inspect docs",
            "--model",
            "local-stub",
            "--kind",
            "subagent",
            "--parent-id",
            parent_id,
            "--root",
            str(tmp_path),
        ],
    )
    list_result = runner.invoke(app, ["agents", "list", "--root", str(tmp_path)])

    assert subagent.exit_code == 0
    assert "subagent" in list_result.output
    assert parent_id in list_result.output


def test_agents_cli_writes_traces_without_model_requests(tmp_path):
    result = runner.invoke(
        app,
        [
            "agents",
            "start",
            "--name",
            "Trace Agent",
            "--role",
            "trace",
            "--task",
            "Write trace event",
            "--model",
            "local-stub",
            "--root",
            str(tmp_path),
        ],
    )
    agent_id = _agent_id_from_output(result.output)
    runner.invoke(app, ["agents", "stop", agent_id, "--root", str(tmp_path)])
    runner.invoke(app, ["agents", "clear", "--confirm", "--root", str(tmp_path)])

    trace_path = tmp_path / ".agentos" / "traces" / f"{datetime.now(UTC).date()}.jsonl"
    trace_text = trace_path.read_text(encoding="utf-8")

    assert "agent_started" in trace_text
    assert "agent_stopped" in trace_text
    assert "agent_state_cleared" in trace_text
    assert "model_request_started" not in trace_text


def test_agents_run_requires_tools_flag(tmp_path):
    result = runner.invoke(
        app,
        [
            "agents",
            "run",
            "--task",
            "search memory for architecture",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "Agent tool calling requires --tools." in result.output


def _agent_id_from_output(output: str) -> str:
    for line in output.splitlines():
        if line.startswith("id="):
            return line.split("=", 1)[1].strip()
    raise AssertionError(f"No id line found in output: {output}")
