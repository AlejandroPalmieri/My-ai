from __future__ import annotations

import os
import sqlite3
import sys
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel


class CheckStatus(StrEnum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class DoctorCheck(BaseModel):
    name: str
    status: CheckStatus
    detail: str


class DoctorReport(BaseModel):
    checks: list[DoctorCheck]

    @property
    def healthy(self) -> bool:
        return all(check.status != CheckStatus.FAIL for check in self.checks)


def run_doctor(
    root: Path,
    agentos_executable: Path | None = None,
    shim_path: Path | None = None,
    path_env: str | None = None,
) -> DoctorReport:
    resolved_root = root.resolve()
    executable = agentos_executable or _default_agentos_executable(resolved_root)
    checks = [
        _check_python(),
        _check_project_root(resolved_root),
        _check_agentos_executable(executable),
        _check_sqlite(),
        _check_sqlite_fts5(),
        _check_policies(resolved_root),
    ]
    if os.name == "nt":
        checks.append(
            _check_windows_shim(
                shim_path or _default_windows_shim(),
                executable,
                path_env,
            )
        )
    return DoctorReport(checks=checks)


def _check_python() -> DoctorCheck:
    version = ".".join(str(part) for part in sys.version_info[:3])
    return DoctorCheck(name="python", status=CheckStatus.PASS, detail=f"Python {version}")


def _check_project_root(root: Path) -> DoctorCheck:
    if root.exists() and (root / "pyproject.toml").exists():
        return DoctorCheck(name="project-root", status=CheckStatus.PASS, detail=str(root))
    if root.exists():
        return DoctorCheck(
            name="project-root",
            status=CheckStatus.WARN,
            detail=f"{root} exists, but pyproject.toml was not found",
        )
    return DoctorCheck(name="project-root", status=CheckStatus.FAIL, detail=f"{root} not found")


def _check_agentos_executable(agentos_executable: Path) -> DoctorCheck:
    if agentos_executable.exists():
        return DoctorCheck(
            name="venv-agentos",
            status=CheckStatus.PASS,
            detail=str(agentos_executable),
        )
    return DoctorCheck(
        name="venv-agentos",
        status=CheckStatus.FAIL,
        detail=f"{agentos_executable} not found",
    )


def _check_sqlite() -> DoctorCheck:
    try:
        with sqlite3.connect(":memory:") as connection:
            version = connection.execute("SELECT sqlite_version()").fetchone()[0]
    except sqlite3.Error as error:
        return DoctorCheck(name="sqlite", status=CheckStatus.FAIL, detail=str(error))
    return DoctorCheck(name="sqlite", status=CheckStatus.PASS, detail=f"SQLite {version}")


def _check_sqlite_fts5() -> DoctorCheck:
    try:
        with sqlite3.connect(":memory:") as connection:
            connection.execute("CREATE VIRTUAL TABLE fts_probe USING fts5(content)")
    except sqlite3.Error as error:
        return DoctorCheck(
            name="sqlite-fts5",
            status=CheckStatus.WARN,
            detail=f"FTS5 unavailable; memory search will use LIKE fallback: {error}",
        )
    return DoctorCheck(name="sqlite-fts5", status=CheckStatus.PASS, detail="FTS5 available")


def _check_policies(root: Path) -> DoctorCheck:
    expected_paths = [
        root / "policies" / "sensitive_paths.yaml",
        root / "policies" / "destructive_commands.yaml",
    ]
    missing = [str(path) for path in expected_paths if not path.exists()]
    if not missing:
        return DoctorCheck(name="policies", status=CheckStatus.PASS, detail="policy files found")
    return DoctorCheck(
        name="policies",
        status=CheckStatus.WARN,
        detail="missing policy files: " + ", ".join(missing),
    )


def _check_windows_shim(
    shim_path: Path,
    agentos_executable: Path,
    path_env: str | None,
) -> DoctorCheck:
    if not shim_path.exists():
        return DoctorCheck(
            name="windows-shim",
            status=CheckStatus.WARN,
            detail=f"{shim_path} not found; run scripts\\install-agentos-command.ps1",
        )

    shim_text = shim_path.read_text(encoding="utf-8", errors="ignore")
    expected_executable = str(agentos_executable)
    shim_directory = str(shim_path.parent)
    path_entries = {
        entry.strip().rstrip("\\").lower()
        for entry in (path_env if path_env is not None else os.environ.get("PATH", "")).split(";")
        if entry.strip()
    }
    if shim_directory.rstrip("\\").lower() not in path_entries:
        return DoctorCheck(
            name="windows-shim",
            status=CheckStatus.WARN,
            detail=f"{shim_path} exists, but its directory is not on PATH",
        )
    if expected_executable not in shim_text:
        return DoctorCheck(
            name="windows-shim",
            status=CheckStatus.WARN,
            detail=f"{shim_path} does not point to {agentos_executable}",
        )
    return DoctorCheck(name="windows-shim", status=CheckStatus.PASS, detail=str(shim_path))


def _default_agentos_executable(root: Path) -> Path:
    if os.name == "nt":
        return root / ".venv" / "Scripts" / "agentos.exe"
    return root / ".venv" / "bin" / "agentos"


def _default_windows_shim() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "Microsoft" / "WindowsApps" / "agentos.cmd"
    return Path.home() / "AppData" / "Local" / "Microsoft" / "WindowsApps" / "agentos.cmd"
