from agentos.diagnostics.doctor import CheckStatus, run_doctor


def test_run_doctor_reports_core_local_environment(tmp_path):
    venv_agentos = tmp_path / ".venv" / "Scripts" / "agentos.exe"
    shim_path = tmp_path / "bin" / "agentos.cmd"
    venv_agentos.parent.mkdir(parents=True)
    shim_path.parent.mkdir(parents=True)
    venv_agentos.write_text("", encoding="utf-8")
    shim_path.write_text(f'@echo off\n"{venv_agentos}" %*\n', encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (tmp_path / "policies").mkdir()
    (tmp_path / "policies" / "sensitive_paths.yaml").write_text("blocked_paths: []\n")
    (tmp_path / "policies" / "destructive_commands.yaml").write_text("blocked_commands: []\n")

    report = run_doctor(
        root=tmp_path,
        agentos_executable=venv_agentos,
        shim_path=shim_path,
        path_env=str(shim_path.parent),
    )

    checks = {check.name: check for check in report.checks}
    assert report.healthy is True
    assert checks["python"].status == CheckStatus.PASS
    assert checks["project-root"].status == CheckStatus.PASS
    assert checks["venv-agentos"].status == CheckStatus.PASS
    assert checks["sqlite"].status == CheckStatus.PASS
    assert checks["sqlite-fts5"].status in {CheckStatus.PASS, CheckStatus.WARN}
    assert checks["policies"].status == CheckStatus.PASS
    assert checks["windows-shim"].status == CheckStatus.PASS
    assert "agentos.cmd" in checks["windows-shim"].detail


def test_run_doctor_fails_when_agentos_executable_is_missing(tmp_path):
    missing_executable = tmp_path / ".venv" / "Scripts" / "agentos.exe"

    report = run_doctor(
        root=tmp_path,
        agentos_executable=missing_executable,
        shim_path=tmp_path / "bin" / "agentos.cmd",
        path_env="",
    )

    checks = {check.name: check for check in report.checks}
    assert report.healthy is False
    assert checks["venv-agentos"].status == CheckStatus.FAIL
