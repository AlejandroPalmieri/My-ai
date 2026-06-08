from typer.testing import CliRunner

from agentos.cli.app import app, main

runner = CliRunner()


def test_no_subcommand_starts_interactive_cli_and_exits_on_exit(tmp_path):
    result = runner.invoke(app, ["--root", str(tmp_path)], input="exit\n")

    assert result.exit_code == 0
    assert "AgentOS Interactive CLI" in result.output
    assert "Type 'help' for commands" in result.output


def test_entrypoint_forwards_unknown_options_to_interactive_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("typer.prompt", lambda *args, **kwargs: "exit")

    main(["--root", str(tmp_path), "--model", "local", "--profile", "godot"])

    output = capsys.readouterr().out
    assert "Forwarded options: --model local --profile godot" in output
