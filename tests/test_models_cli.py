from typer.testing import CliRunner

from agentos.cli.app import app

runner = CliRunner()


def test_models_cli_init_list_show_set_status_usage(tmp_path):
    init_result = runner.invoke(app, ["models", "init", "--root", str(tmp_path)])
    list_result = runner.invoke(app, ["models", "list", "--root", str(tmp_path)])
    show_result = runner.invoke(app, ["models", "show", "--root", str(tmp_path)])
    set_result = runner.invoke(
        app,
        ["models", "set", "ollama-local", "--root", str(tmp_path)],
    )
    status_result = runner.invoke(app, ["models", "status", "--root", str(tmp_path)])
    usage_result = runner.invoke(app, ["models", "usage", "--root", str(tmp_path)])

    assert init_result.exit_code == 0
    assert "Model config initialized" in init_result.output
    assert (tmp_path / ".agentos" / "models.yaml").exists()
    assert list_result.exit_code == 0
    assert "local-stub" in list_result.output
    assert "openai-gpt-5-5-thinking" in list_result.output
    assert show_result.exit_code == 0
    assert "Active model profile" in show_result.output
    assert set_result.exit_code == 0
    assert "ollama-local" in set_result.output
    assert status_result.exit_code == 0
    assert "configured" in status_result.output
    assert usage_result.exit_code == 0
    assert "cumulative_total_tokens" in usage_result.output


def test_models_cli_reset_usage_requires_confirm(tmp_path):
    runner.invoke(app, ["models", "init", "--root", str(tmp_path)])

    rejected = runner.invoke(app, ["models", "reset-usage", "--root", str(tmp_path)])
    accepted = runner.invoke(
        app,
        ["models", "reset-usage", "--confirm", "--root", str(tmp_path)],
    )

    assert rejected.exit_code == 1
    assert "--confirm" in rejected.output
    assert accepted.exit_code == 0
    assert "Usage reset" in accepted.output


def test_models_cli_missing_api_key_warns_without_crashing(tmp_path, monkeypatch):
    runner.invoke(app, ["models", "init", "--root", str(tmp_path)])
    runner.invoke(app, ["models", "set", "openai-gpt-5-5", "--root", str(tmp_path)])
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    status_result = runner.invoke(app, ["models", "status", "--root", str(tmp_path)])

    assert status_result.exit_code == 0
    assert "not configured" in status_result.output
    assert "OPENAI_API_KEY" in status_result.output
