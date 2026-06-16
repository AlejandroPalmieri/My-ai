import json
from datetime import UTC, datetime

from typer.testing import CliRunner

from agentos.cli.app import app

runner = CliRunner()


def test_chat_once_local_stub_cli(tmp_path):
    result = runner.invoke(app, ["chat", "once", "Hello CLI", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "local-stub response" in result.output
    assert "Hello CLI" in result.output


def test_chat_once_json_output(tmp_path):
    result = runner.invoke(
        app,
        ["chat", "once", "JSON please", "--json", "--root", str(tmp_path)],
    )

    payload = json.loads(result.output)

    assert result.exit_code == 0
    assert payload["provider"] == "local"
    assert payload["model_profile"] == "local-stub"
    assert payload["usage"]["total_tokens"] > 0


def test_chat_once_missing_api_key_prints_guidance_without_traceback(tmp_path, monkeypatch):
    runner.invoke(app, ["models", "init", "--root", str(tmp_path)])
    runner.invoke(app, ["models", "set", "openrouter-auto", "--root", str(tmp_path)])
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    result = runner.invoke(app, ["chat", "once", "hello", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "OPENROUTER_API_KEY" in result.output
    assert "Traceback" not in result.output


def test_chat_status_cli(tmp_path):
    result = runner.invoke(app, ["chat", "status", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "local-stub" in result.output
    assert "configured" in result.output


def test_chat_once_creates_trace_events(tmp_path):
    result = runner.invoke(app, ["chat", "once", "trace cli", "--root", str(tmp_path)])

    assert result.exit_code == 0
    trace_path = tmp_path / ".agentos" / "traces" / f"{datetime.now(UTC).date()}.jsonl"
    trace_text = trace_path.read_text(encoding="utf-8")
    assert "model_request_started" in trace_text
    assert "model_request_completed" in trace_text
    assert "model_usage_updated" in trace_text


def test_chat_once_stream_cli_prints_expected_content(tmp_path):
    result = runner.invoke(
        app,
        ["chat", "once", "hello streaming", "--stream", "--root", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "local-stub response" in result.output
    assert "hello streaming" in result.output
    assert "model=local-stub" in result.output


def test_chat_once_no_stream_cli_remains_supported(tmp_path):
    result = runner.invoke(
        app,
        ["chat", "once", "hello no stream", "--no-stream", "--root", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "hello no stream" in result.output
