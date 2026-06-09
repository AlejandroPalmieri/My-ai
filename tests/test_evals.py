import json

from agentos.evals.runner import EvalRunner


def test_eval_runner_executes_local_cases_and_writes_results(tmp_path):
    runner = EvalRunner(tmp_path)

    report = runner.run()

    assert report.passed is True
    assert {case.name for case in report.cases} == {
        "memory_search",
        "policy_check",
        "skill_validation",
        "sdd_workflow",
    }
    assert report.result_path is not None
    assert report.result_path.parent == tmp_path / ".agentos" / "evals" / "results"
    assert report.result_path.exists()

    payload = json.loads(report.result_path.read_text(encoding="utf-8"))
    assert payload["summary"]["passed"] == 4
    assert payload["summary"]["failed"] == 0


def test_eval_runner_result_payload_uses_stable_fields(tmp_path):
    report = EvalRunner(tmp_path).run()
    payload = json.loads(report.result_path.read_text(encoding="utf-8"))

    assert set(payload) == {"id", "timestamp", "passed", "summary", "cases"}
    assert all(
        {"name", "status", "detail", "duration_ms"}.issubset(case)
        for case in payload["cases"]
    )
