import json

from typer.testing import CliRunner

from agentos.cli.app import app
from agentos.usage.store import UsageStore

runner = CliRunner()


def test_usage_summary_cli(tmp_path):
    UsageStore(tmp_path).record_event(
        session_id="session-1",
        project="default",
        profile="default",
        provider="local",
        model="local-stub",
        effort="medium",
        agent_id=None,
        command="chat.once",
        input_tokens=10,
        output_tokens=5,
        estimated_cost_usd=0.0,
        context_used_percent=1.0,
    )

    result = runner.invoke(app, ["usage", "summary", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "total_tokens" in result.output
    assert "15" in result.output


def test_usage_export_json_cli(tmp_path):
    UsageStore(tmp_path).record_event(
        session_id="session-1",
        project="default",
        profile="default",
        provider="local",
        model="local-stub",
        effort="medium",
        agent_id="agent-1",
        command="chat.once",
        input_tokens=10,
        output_tokens=5,
        estimated_cost_usd=None,
        context_used_percent=1.0,
    )

    result = runner.invoke(app, ["usage", "export", "--format", "json", "--root", str(tmp_path)])
    payload = json.loads(result.output)

    assert result.exit_code == 0
    assert payload["events"][0]["agent_id"] == "agent-1"
    assert "prompt" not in payload["events"][0]


def test_usage_reset_cli_requires_confirm(tmp_path):
    UsageStore(tmp_path).record_event(
        session_id="session-1",
        project="default",
        profile="default",
        provider="local",
        model="local-stub",
        effort="medium",
        agent_id=None,
        command="chat.once",
        input_tokens=1,
        output_tokens=1,
        estimated_cost_usd=0.0,
        context_used_percent=1.0,
    )

    rejected = runner.invoke(app, ["usage", "reset", "--root", str(tmp_path)])
    accepted = runner.invoke(app, ["usage", "reset", "--confirm", "--root", str(tmp_path)])

    assert rejected.exit_code == 1
    assert "--confirm" in rejected.output
    assert accepted.exit_code == 0
    assert UsageStore(tmp_path).events() == []
