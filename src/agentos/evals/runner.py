from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from agentos.services.local import (
    LocalPolicyService,
    LocalSDDService,
    LocalSkillRegistryService,
    LocalTechnicalMemoryService,
)


@dataclass(frozen=True)
class EvalCaseResult:
    name: str
    status: str
    detail: str
    duration_ms: int

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
            "duration_ms": self.duration_ms,
        }


@dataclass(frozen=True)
class EvalReport:
    id: str
    timestamp: str
    cases: list[EvalCaseResult]
    result_path: Path

    @property
    def passed(self) -> bool:
        return all(case.passed for case in self.cases)

    @property
    def summary(self) -> dict[str, int]:
        passed = sum(1 for case in self.cases if case.passed)
        failed = len(self.cases) - passed
        return {"passed": passed, "failed": failed, "total": len(self.cases)}

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "passed": self.passed,
            "summary": self.summary,
            "cases": [case.to_dict() for case in self.cases],
        }


class EvalRunner:
    """Runs local safety and workflow checks without touching production data."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.results_dir = root / ".agentos" / "evals" / "results"
        self.workspace_dir = root / ".agentos" / "evals" / "workspace"

    def run(self) -> EvalReport:
        run_id = uuid4().hex
        timestamp = datetime.now(UTC).isoformat()
        cases: list[EvalCaseResult] = []
        workspace = self.workspace_dir / run_id
        case_specs = [
            ("memory_search", self._run_memory_search),
            ("policy_check", self._run_policy_check),
            ("skill_validation", self._run_skill_validation),
            ("sdd_workflow", self._run_sdd_workflow),
        ]
        for name, case in case_specs:
            cases.append(self._run_case(name, case, workspace / name))

        self.results_dir.mkdir(parents=True, exist_ok=True)
        result_path = self.results_dir / f"{timestamp[:10]}-{run_id}.json"
        report = EvalReport(
            id=run_id,
            timestamp=timestamp,
            cases=cases,
            result_path=result_path,
        )
        result_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        return report

    def _run_case(self, name: str, case, workspace: Path) -> EvalCaseResult:
        started = perf_counter()
        try:
            workspace.mkdir(parents=True, exist_ok=True)
            detail = case(workspace)
            status = "passed"
        except Exception as error:  # pragma: no cover - exercised by future failing evals
            detail = str(error)
            status = "failed"
        duration_ms = int((perf_counter() - started) * 1000)
        return EvalCaseResult(
            name=name,
            status=status,
            detail=detail,
            duration_ms=duration_ms,
        )

    def _run_memory_search(self, workspace: Path) -> str:
        memory = LocalTechnicalMemoryService(workspace)
        added = memory.add_memory(
            project="eval",
            title="Eval memory",
            kind="note",
            content="AgentOS eval memory search checks local SQLite retrieval.",
            tags=["eval"],
        )
        results = memory.search_memories("SQLite retrieval", project="eval")
        if not any(result.id == added.id for result in results):
            raise AssertionError("Expected indexed memory was not returned.")
        return "Memory add/search returned the expected local record."

    def _run_policy_check(self, workspace: Path) -> str:
        policy = LocalPolicyService(workspace)
        blocked = policy.check_path(".env")
        allowed = policy.check_command("pytest")
        if blocked.allowed:
            raise AssertionError("Sensitive .env path was not blocked.")
        if not allowed.allowed:
            raise AssertionError("Safe pytest command was not allowed.")
        return "Policy checker blocked a sensitive path and allowed a safe command."

    def _run_skill_validation(self, workspace: Path) -> str:
        skill_dir = workspace / "skills" / "eval-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: eval-skill\ndescription: Eval validation skill.\n---\n",
            encoding="utf-8",
        )
        validation = LocalSkillRegistryService(workspace).validate()
        if not validation.valid:
            raise AssertionError("; ".join(validation.errors))
        return "Skill registry validation accepted a minimal valid SKILL.md."

    def _run_sdd_workflow(self, workspace: Path) -> str:
        sdd = LocalSDDService(workspace)
        change = sdd.create_change("eval-sdd-workflow")
        advanced = sdd.advance_change("eval-sdd-workflow", "explore")
        if not (change.path / "proposal.md").exists():
            raise AssertionError("SDD proposal artifact was not created.")
        if advanced.phase != "explore":
            raise AssertionError("SDD change did not advance to explore.")
        return "SDD change artifacts were created and advanced to explore."
