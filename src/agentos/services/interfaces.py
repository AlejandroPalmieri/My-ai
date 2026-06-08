from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from agentos.brain.store import BrainChunk, BrainDocument, BrainSearchResult
from agentos.config.profiles import ProfileValidation, ProjectProfile
from agentos.diagnostics.doctor import DoctorReport
from agentos.logging.traces import TraceEvent, TraceLogger
from agentos.memory.store import Memory
from agentos.policies.checker import PolicyResult, PolicyRule
from agentos.sdd.generator import SDDChange
from agentos.skills.registry import SkillContent, SkillRegistry, SkillValidation


@runtime_checkable
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


@runtime_checkable
class StrategicBrainService(Protocol):
    def ingest_document(self, path: Path) -> BrainDocument: ...

    def search_documents(self, query: str, limit: int = 20) -> list[BrainSearchResult]: ...

    def list_documents(self) -> list[BrainDocument]: ...

    def get_document(self, document_id: str) -> BrainDocument | None: ...

    def list_document_chunks(self, document_id: str) -> list[BrainChunk]: ...

    def synthesize(self, topic: str) -> str: ...


@runtime_checkable
class SkillRegistryService(Protocol):
    def scan(self) -> SkillRegistry: ...

    def list(self) -> SkillRegistry: ...

    def show(self, skill_name: str) -> SkillContent: ...

    def validate(self) -> SkillValidation: ...


@runtime_checkable
class PolicyService(Protocol):
    def check_path(self, path: str) -> PolicyResult: ...

    def check_command(self, command: str) -> PolicyResult: ...

    def list_rules(self) -> list[PolicyRule]: ...

    def explain(self) -> str: ...


@runtime_checkable
class SDDService(Protocol):
    def create_change(self, change_name: str) -> SDDChange: ...

    def list_changes(self) -> list[SDDChange]: ...

    def get_status(self, change_name: str) -> SDDChange: ...

    def advance_change(self, change_name: str, phase: str, force: bool = False) -> SDDChange: ...

    def archive_change(self, change_name: str) -> SDDChange: ...


@runtime_checkable
class TraceService(Protocol):
    def start(self, command: str) -> TraceLogger: ...

    def complete(
        self,
        command: str,
        trace: TraceLogger,
        payload: dict[str, object] | None = None,
    ) -> None: ...

    def fail(self, command: str, trace: TraceLogger, error: str) -> None: ...

    def list_dates(self) -> list[str]: ...

    def read(self, trace_date: str) -> list[TraceEvent]: ...

    def tail(self, limit: int = 20) -> list[TraceEvent]: ...

    def export(self, trace_date: str | None = None) -> list[str]: ...


@runtime_checkable
class ProfileService(Protocol):
    def create_default(self) -> Path: ...

    def load(self) -> ProjectProfile: ...

    def set_active(self, profile_name: str) -> ProjectProfile: ...

    def validate(self, known_skills: set[str] | None = None) -> ProfileValidation: ...

    def resolve_memory_project(self, project: str | None = None) -> str: ...


@runtime_checkable
class DoctorService(Protocol):
    def run(self) -> DoctorReport: ...


@runtime_checkable
class RefinerService(Protocol):
    def analyze_trace(self, trace_path: Path) -> str: ...
