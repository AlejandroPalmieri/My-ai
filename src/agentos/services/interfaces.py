from __future__ import annotations

from pathlib import Path
from typing import Protocol

from agentos.memory.store import Memory
from agentos.policies.checker import PolicyResult
from agentos.sdd.generator import SDDChange
from agentos.skills.registry import SkillContent, SkillRegistry, SkillValidation


class TechnicalMemoryService(Protocol):
    def add_memory(
        self,
        project: str,
        title: str,
        kind: str,
        content: str,
        tags: list[str],
        source: str | None = None,
        confidence: float = 1.0,
    ) -> Memory: ...

    def search_memories(
        self,
        query: str,
        project: str | None = None,
        limit: int = 20,
    ) -> list[Memory]: ...

    def export_memories(self, path: Path) -> int: ...

    def import_memories(self, path: Path) -> int: ...

    def list_memories(
        self,
        project: str | None = None,
        kind: str | None = None,
        limit: int | None = None,
    ) -> list[Memory]: ...

    def get_memory(self, memory_id: str) -> Memory | None: ...

    def delete_memory(self, memory_id: str) -> bool: ...


class StrategicBrainService(Protocol):
    def synthesize(self, topic: str) -> str: ...


class SkillRegistryService(Protocol):
    def scan(self) -> SkillRegistry: ...

    def list(self) -> SkillRegistry: ...

    def show(self, skill_name: str) -> SkillContent: ...

    def validate(self) -> SkillValidation: ...


class PolicyService(Protocol):
    def check_path(self, path: str) -> PolicyResult: ...

    def check_command(self, command: str) -> PolicyResult: ...


class SDDService(Protocol):
    def create_change(self, change_name: str) -> SDDChange: ...

    def list_changes(self) -> list[SDDChange]: ...

    def get_status(self, change_name: str) -> SDDChange: ...

    def advance_change(self, change_name: str, phase: str, force: bool = False) -> SDDChange: ...

    def archive_change(self, change_name: str) -> SDDChange: ...


class RefinerService(Protocol):
    def analyze_trace(self, trace_path: Path) -> str: ...
