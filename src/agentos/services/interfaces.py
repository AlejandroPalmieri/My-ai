from __future__ import annotations

from pathlib import Path
from typing import Protocol

from agentos.memory.store import Memory
from agentos.policies.checker import PolicyResult
from agentos.sdd.generator import SDDChange
from agentos.skills.registry import SkillRegistry


class TechnicalMemoryService(Protocol):
    def add_memory(
        self,
        project: str,
        title: str,
        kind: str,
        content: str,
        tags: list[str],
    ) -> Memory: ...

    def search_memories(
        self,
        query: str,
        project: str | None = None,
        limit: int = 20,
    ) -> list[Memory]: ...

    def export_memories(self, path: Path) -> int: ...

    def import_memories(self, path: Path) -> int: ...


class StrategicBrainService(Protocol):
    def synthesize(self, topic: str) -> str: ...


class SkillRegistryService(Protocol):
    def scan(self) -> SkillRegistry: ...


class PolicyService(Protocol):
    def check_path(self, path: str) -> PolicyResult: ...

    def check_command(self, command: str) -> PolicyResult: ...


class SDDService(Protocol):
    def create_change(self, change_name: str) -> SDDChange: ...


class RefinerService(Protocol):
    def analyze_trace(self, trace_path: Path) -> str: ...
