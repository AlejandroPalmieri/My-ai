import json

from typer.testing import CliRunner

from agentos.cli.app import app
from agentos.evals.cases import EvalCase, EvalContext
from agentos.evals.reports import redact_report_payload, safe_report_text
from agentos.evals.runner import EvalRunner

runner = CliRunner()


def test_eval_runner_filters_by_category(tmp_path):
    report = EvalRunner(tmp_path).run(category="providers")

    assert report.passed is True
    assert report.category == "provider_evals"
    assert {case.category for case in report.cases} == {"provider_evals"}
    assert {case.name for case in report.cases} == {
        "local_stub_non_streaming",
        "local_stub_streaming",
        "missing_api_key_warning",
        "provider_factory_selects_adapter",
    }


def test_eval_runner_writes_json_report(tmp_path):
    report = EvalRunner(tmp_path).run(category="safety")

    assert report.result_path is not None
    assert report.result_path.parent == tmp_path / ".agentos" / "evals" / "results"
    assert report.result_path.exists()

    payload = json.loads(report.result_path.read_text(encoding="utf-8"))
    assert payload["id"] == report.id
    assert payload["category"] == "safety_evals"
    assert payload["summary"]["passed"] == 4
    assert payload["summary"]["failed"] == 0
    assert payload["agentos_version"]
    assert payload["environment"]["root"] == str(tmp_path)


def test_eval_runner_writes_markdown_report(tmp_path):
    report = EvalRunner(tmp_path).run(category="providers")

    assert report.markdown_path is not None
    assert report.markdown_path.exists()
    markdown = report.markdown_path.read_text(encoding="utf-8")
    assert f"AgentOS Eval Report `{report.id}`" in markdown
    assert "provider_evals" in markdown


def test_failing_eval_is_captured(tmp_path):
    def fail(_context: EvalContext) -> str:
        raise AssertionError("intentional failure")

    case = EvalCase(
        name="failing_eval",
        category="safety_evals",
        description="Intentional failure",
        run=fail,
    )

    report = EvalRunner(tmp_path, cases=[case]).run()

    assert report.passed is False
    assert report.summary["failed"] == 1
    assert report.failures[0]["name"] == "failing_eval"
    assert "intentional failure" in report.failures[0]["detail"]
    assert report.result_path is not None
    assert report.markdown_path is not None
    payload = json.loads(report.result_path.read_text(encoding="utf-8"))
    markdown = report.markdown_path.read_text(encoding="utf-8")
    assert payload["passed"] is False
    assert payload["summary"]["failed"] == 1
    assert payload["failures"][0]["name"] == "failing_eval"
    assert "intentional failure" in payload["failures"][0]["detail"]
    assert "failing_eval" in markdown
    assert "intentional failure" in markdown


def test_eval_reports_redact_sensitive_failure_details(tmp_path):
    raw_secret = "sk-agentoseval123"

    def fail(_context: EvalContext) -> str:
        raise AssertionError(
            f"failed reading .env token=abc123 api_key={raw_secret} /home/user/.ssh/id_rsa"
        )

    case = EvalCase(
        name="secret_failure",
        category="safety_evals",
        description="Sensitive failure",
        run=fail,
    )

    report = EvalRunner(tmp_path, cases=[case]).run()

    assert report.result_path is not None
    assert report.markdown_path is not None
    json_text = report.result_path.read_text(encoding="utf-8")
    markdown = report.markdown_path.read_text(encoding="utf-8")
    result = runner.invoke(app, ["eval", "report", report.id, "--root", str(tmp_path)])

    assert result.exit_code == 0
    for output in (json_text, markdown, result.output):
        assert raw_secret not in output
        assert "abc123" not in output
        assert ".ssh" not in output
        assert ".env" not in output
        assert "[REDACTED]" in output


def test_eval_reports_redact_common_credential_patterns():
    database_url = "postgres://agent:secret@localhost/agentos"
    bearer_token = "standalone-bearer-token"
    authorization_token = "authorization-token"
    jwt_token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJldmFscyJ9.c2lnbmF0dXJlMTIzNDU2"

    redacted = safe_report_text(
        f"DATABASE_URL={database_url} Authorization: Bearer {authorization_token} "
        f"Bearer {bearer_token} jwt={jwt_token}"
    )
    payload = redact_report_payload(
        {
            "DATABASE_URL": database_url,
            "headers": {"Authorization": f"Bearer {authorization_token}"},
        }
    )

    assert database_url not in redacted
    assert authorization_token not in redacted
    assert bearer_token not in redacted
    assert jwt_token not in redacted
    assert "DATABASE_URL=[REDACTED]" in redacted
    assert "Authorization: Bearer [REDACTED]" in redacted
    assert "Bearer [REDACTED]" in redacted
    assert payload["DATABASE_URL"] == "[REDACTED]"
    assert payload["headers"]["Authorization"] == "[REDACTED]"


def test_latest_report_command_works(tmp_path):
    report = EvalRunner(tmp_path).run(category="safety")

    result = runner.invoke(app, ["eval", "report", "--latest", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert report.id in result.output
    assert "passed=4" in result.output
    assert "failed=0 skipped=0" in result.output


def test_report_command_by_id_works(tmp_path):
    report = EvalRunner(tmp_path).run(category="safety")

    result = runner.invoke(app, ["eval", "report", report.id, "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert report.id in result.output
    assert "passed=4" in result.output
    assert "failed=0 skipped=0" in result.output


def test_report_command_rejects_path_traversal_ids(tmp_path):
    arbitrary_report = tmp_path / ".agentos" / "evals" / "secret-report.json"
    arbitrary_report.parent.mkdir(parents=True)
    arbitrary_report.write_text(
        json.dumps(
            {
                "id": "secret-report",
                "category": "safety_evals",
                "summary": {"passed": 0, "failed": 0, "skipped": 0},
                "cases": [{"detail": "SHOULD_NOT_PRINT"}],
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["eval", "report", "../secret-report", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "Invalid eval report id." in result.output
    assert "SHOULD_NOT_PRINT" not in result.output


def test_report_commands_reject_symlinked_results_dir(tmp_path):
    outside_results = tmp_path / "outside-results"
    outside_results.mkdir()
    outside_payload = {
        "id": "external-report",
        "category": "safety_evals",
        "summary": {"passed": 0, "failed": 1, "skipped": 0},
        "cases": [{"detail": "OUTSIDE_SECRET"}],
    }
    (outside_results / "external-report.json").write_text(
        json.dumps(outside_payload), encoding="utf-8"
    )
    evals_dir = tmp_path / ".agentos" / "evals"
    evals_dir.mkdir(parents=True)
    (evals_dir / "results").symlink_to(outside_results, target_is_directory=True)

    by_id = runner.invoke(app, ["eval", "report", "external-report", "--root", str(tmp_path)])
    latest = runner.invoke(app, ["eval", "report", "--latest", "--root", str(tmp_path)])

    for result in (by_id, latest):
        assert result.exit_code == 1
        assert "Invalid eval results directory." in result.output
        assert "OUTSIDE_SECRET" not in result.output


def test_eval_run_rejects_symlinked_results_dir_on_write(tmp_path):
    outside_results = tmp_path / "outside-results"
    outside_results.mkdir()
    evals_dir = tmp_path / ".agentos" / "evals"
    evals_dir.mkdir(parents=True)
    (evals_dir / "results").symlink_to(outside_results, target_is_directory=True)

    result = runner.invoke(app, ["eval", "run", "--category", "safety", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "Invalid eval results directory." in result.output
    assert list(outside_results.iterdir()) == []


def test_safety_evals_pass(tmp_path):
    report = EvalRunner(tmp_path).run(category="safety")

    assert report.passed is True
    assert {case.name for case in report.cases} == {
        "no_env_read",
        "no_api_key_printed",
        "no_shell_execution_tool_exposed",
        "destructive_command_blocked",
    }


def test_eval_cli_run_category_providers(tmp_path):
    result = runner.invoke(app, ["eval", "run", "--category", "providers", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "category=provider_evals" in result.output
    assert "failed=0" in result.output
