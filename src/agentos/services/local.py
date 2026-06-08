from __future__ import annotations

from pathlib import Path

from agentos.memory.store import Memory, MemoryStore
from agentos.policies.checker import PolicyChecker, PolicyResult, create_default_policies
from agentos.sdd.generator import SDDChange, create_change
from agentos.skills.registry import SkillRegistry, scan_skills


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
    ) -> Memory:
        return self.store.add_memory(project, title, kind, content, tags)

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


class LocalStrategicBrainService:
    def synthesize(self, topic: str) -> str:
        return f"Strategic synthesis is a Phase 2 service boundary stub for: {topic}"


class LocalSkillRegistryService:
    def __init__(self, root: Path) -> None:
        self.root = root

    def scan(self) -> SkillRegistry:
        return scan_skills(self.root)


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


class LocalRefinerService:
    def analyze_trace(self, trace_path: Path) -> str:
        return f"Refiner analysis is a Phase 2 service boundary stub for: {trace_path}"
