from __future__ import annotations

from pathlib import Path

from agentos.diagnostics.doctor import DoctorReport, run_doctor
from agentos.memory.store import Memory, MemoryStore
from agentos.policies.checker import PolicyChecker, PolicyResult, create_default_policies
from agentos.sdd.generator import (
    SDDChange,
    advance_change,
    archive_change,
    create_change,
    get_change_status,
    list_changes,
)
from agentos.skills.registry import (
    SkillContent,
    SkillRegistry,
    SkillValidation,
    scan_skills,
    show_skill,
    validate_skills,
)


class LocalTechnicalMemoryService:
    def __init__(self, root: Path) -> None:
        self.store = MemoryStore(root)

    def add_memory(
        self,
        project: str,
        title: str,
        kind: str,
        content: str,
        tags: list[str],
        source: str | None = None,
        confidence: float = 1.0,
    ) -> Memory:
        return self.store.add_memory(project, title, kind, content, tags, source, confidence)

    def search_memories(
        self,
        query: str,
        project: str | None = None,
        limit: int = 20,
    ) -> list[Memory]:
        return self.store.search(query, project=project, limit=limit)

    def export_memories(self, path: Path) -> int:
        return self.store.export_json(path)

    def import_memories(self, path: Path) -> int:
        return self.store.import_json(path)

    def list_memories(
        self,
        project: str | None = None,
        kind: str | None = None,
        limit: int | None = None,
    ) -> list[Memory]:
        return self.store.list_memories(project=project, kind=kind, limit=limit)

    def get_memory(self, memory_id: str) -> Memory | None:
        return self.store.get_memory(memory_id)

    def delete_memory(self, memory_id: str) -> bool:
        return self.store.delete_memory(memory_id)


class LocalStrategicBrainService:
    def synthesize(self, topic: str) -> str:
        return f"Strategic synthesis is a Phase 2 service boundary stub for: {topic}"


class LocalSkillRegistryService:
    def __init__(self, root: Path) -> None:
        self.root = root

    def scan(self) -> SkillRegistry:
        return scan_skills(self.root)

    def list(self) -> SkillRegistry:
        return scan_skills(self.root)

    def show(self, skill_name: str) -> SkillContent:
        return show_skill(self.root, skill_name)

    def validate(self) -> SkillValidation:
        return validate_skills(self.root)


class LocalPolicyService:
    def __init__(self, root: Path) -> None:
        create_default_policies(root)
        self.checker = PolicyChecker.from_directory(root / "policies")

    def check_path(self, path: str) -> PolicyResult:
        return self.checker.check_path(path)

    def check_command(self, command: str) -> PolicyResult:
        return self.checker.check_command(command)


class LocalSDDService:
    def __init__(self, root: Path) -> None:
        self.root = root

    def create_change(self, change_name: str) -> SDDChange:
        return create_change(self.root, change_name)

    def list_changes(self) -> list[SDDChange]:
        return list_changes(self.root)

    def get_status(self, change_name: str) -> SDDChange:
        return get_change_status(self.root, change_name)

    def advance_change(self, change_name: str, phase: str, force: bool = False) -> SDDChange:
        return advance_change(self.root, change_name, phase, force=force)

    def archive_change(self, change_name: str) -> SDDChange:
        return archive_change(self.root, change_name)


class LocalDoctorService:
    def __init__(self, root: Path) -> None:
        self.root = root

    def run(self) -> DoctorReport:
        return run_doctor(self.root)


class LocalRefinerService:
    def analyze_trace(self, trace_path: Path) -> str:
        return f"Refiner analysis is a Phase 2 service boundary stub for: {trace_path}"
