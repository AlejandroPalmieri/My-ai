from __future__ import annotations

import platform
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from agentos import __version__
from agentos.evals.cases import EvalCase, EvalContext, builtin_cases, normalize_category
from agentos.evals.reports import report_paths, safe_report_text, write_report


@dataclass(frozen=True)
class EvalCaseResult:
    name: str
    category: str
    status: str
    detail: str
    duration_ms: int

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "category": self.category,
            "status": self.status,
            "detail": safe_report_text(self.detail),
            "duration_ms": self.duration_ms,
        }


@dataclass(frozen=True)
class EvalReport:
    id: str
    timestamp: str
    category: str
    cases: list[EvalCaseResult]
    duration_ms: int
    result_path: Path | None = None
    markdown_path: Path | None = None
    environment: dict[str, str] = field(default_factory=dict)
    agentos_version: str = __version__

    @property
    def passed(self) -> bool:
        return all(case.passed for case in self.cases)

    @property
    def summary(self) -> dict[str, int]:
        passed = sum(1 for case in self.cases if case.passed)
        failed = sum(1 for case in self.cases if case.status == "failed")
        skipped = sum(1 for case in self.cases if case.status == "skipped")
        return {"passed": passed, "failed": failed, "skipped": skipped, "total": len(self.cases)}

    @property
    def failures(self) -> list[dict[str, str]]:
        return [
            {"name": case.name, "category": case.category, "detail": case.detail}
            for case in self.cases
            if case.status == "failed"
        ]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "category": self.category,
            "passed": self.passed,
            "summary": self.summary,
            "duration_ms": self.duration_ms,
            "failed": self.summary["failed"],
            "skipped": self.summary["skipped"],
            "failures": self.failures,
            "environment": self.environment,
            "agentos_version": self.agentos_version,
            "result_path": str(self.result_path) if self.result_path else None,
            "markdown_path": str(self.markdown_path) if self.markdown_path else None,
            "cases": [case.to_dict() for case in self.cases],
        }


class EvalRunner:
    """Runs local safety and workflow checks without touching production data."""

    def __init__(self, root: Path, cases: list[EvalCase] | None = None) -> None:
        self.root = root
        self.workspace_dir = root / ".agentos" / "evals" / "workspace"
        self.cases = cases or builtin_cases()

    def run(self, category: str | None = None) -> EvalReport:
        run_id = f"eval-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
        timestamp = datetime.now(UTC).isoformat()
        cases: list[EvalCaseResult] = []
        workspace = self.workspace_dir / run_id
        selected_category = normalize_category(category)
        selected_cases = [
            case
            for case in self.cases
            if selected_category is None or case.category == selected_category
        ]
        started = perf_counter()
        for case in selected_cases:
            cases.append(self._run_case(case, workspace / case.category / case.name))
        duration_ms = int((perf_counter() - started) * 1000)
        result_path, markdown_path = report_paths(self.root, run_id)
        report = EvalReport(
            id=run_id,
            timestamp=timestamp,
            category=selected_category or "all",
            cases=cases,
            duration_ms=duration_ms,
            result_path=result_path,
            markdown_path=markdown_path,
            environment=_environment_summary(self.root),
        )
        write_report(self.root, report)
        return report

    def _run_case(self, case: EvalCase, workspace: Path) -> EvalCaseResult:
        started = perf_counter()
        try:
            workspace.mkdir(parents=True, exist_ok=True)
            detail = case.run(EvalContext(root=self.root, workspace=workspace))
            status = "passed"
        except Exception as error:
            detail = safe_report_text(error)
            status = "failed"
        duration_ms = int((perf_counter() - started) * 1000)
        return EvalCaseResult(
            name=case.name,
            category=case.category,
            status=status,
            detail=detail,
            duration_ms=duration_ms,
        )


def _environment_summary(root: Path) -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "platform": platform.system().lower() or "unknown",
        "root": str(root),
    }
