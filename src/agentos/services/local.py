from __future__ import annotations

from pathlib import Path

from agentos.brain.store import BrainChunk, BrainDocument, BrainSearchResult, StrategicBrainStore
from agentos.config.profiles import (
    ProfileValidation,
    ProjectProfile,
    create_default_profile,
    load_project_profile,
    set_active_profile,
    validate_profile,
)
from agentos.diagnostics.doctor import DoctorReport, run_doctor
from agentos.logging.traces import (
    TraceEvent,
    TraceEventType,
    TraceLogger,
    export_trace_lines,
    list_trace_files,
    read_trace_events,
    tail_trace_events,
)
from agentos.memory.store import Memory, MemoryStore
from agentos.policies.checker import (
    PolicyChecker,
    PolicyResult,
    PolicyRule,
    create_default_policies,
)
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
    def __init__(self, root: Path = Path(".")) -> None:
        self.root = root
        self._store: StrategicBrainStore | None = None

    @property
    def store(self) -> StrategicBrainStore:
        if self._store is None:
            self._store = StrategicBrainStore(self.root)
        return self._store

    def ingest_document(self, path: Path) -> BrainDocument:
        return self.store.ingest_document(path)

    def search_documents(self, query: str, limit: int = 20) -> list[BrainSearchResult]:
        return self.store.search(query, limit=limit)

    def list_documents(self) -> list[BrainDocument]:
        return self.store.list_documents()

    def get_document(self, document_id: str) -> BrainDocument | None:
        return self.store.get_document(document_id)

    def list_document_chunks(self, document_id: str) -> list[BrainChunk]:
        return self.store.list_chunks(document_id)

    def synthesize(self, topic: str) -> str:
        return (
            "TODO: StrategicBrainService is a Phase 2 service boundary stub. "
            "v0 indexes local documents only; no LLM synthesis or full GBrain "
            f"retrieval is implemented yet: {topic}"
        )


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
        try:
            profile = load_project_profile(root)
        except (FileNotFoundError, KeyError, ValueError):
            profile = None
        if profile is not None:
            self.checker.sensitive_paths.extend(profile.active.blocked_paths)

    def check_path(self, path: str) -> PolicyResult:
        return self.checker.check_path(path)

    def check_command(self, command: str) -> PolicyResult:
        return self.checker.check_command(command)

    def list_rules(self) -> list[PolicyRule]:
        return self.checker.list_rules()

    def explain(self) -> str:
        return self.checker.explain()


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


class LocalTraceService:
    def __init__(self, root: Path) -> None:
        self.root = root

    def start(self, command: str) -> TraceLogger:
        trace = TraceLogger(self.root)
        trace.log_event(TraceEventType.COMMAND_STARTED, command=command, status="started")
        return trace

    def complete(
        self,
        command: str,
        trace: TraceLogger,
        payload: dict[str, object] | None = None,
    ) -> None:
        event_payload = {"command": command}
        if payload:
            event_payload.update(payload)
        trace.log_event(
            TraceEventType.COMMAND_COMPLETED,
            command=command,
            status="ok",
            payload=event_payload,
        )

    def fail(self, command: str, trace: TraceLogger, error: str) -> None:
        trace.log_event(
            TraceEventType.COMMAND_FAILED,
            command=command,
            status="failed",
            error=error,
        )

    def list_dates(self) -> list[str]:
        return list_trace_files(self.root)

    def read(self, trace_date: str) -> list[TraceEvent]:
        return read_trace_events(self.root, trace_date)

    def tail(self, limit: int = 20) -> list[TraceEvent]:
        return tail_trace_events(self.root, limit=limit)

    def export(self, trace_date: str | None = None) -> list[str]:
        return export_trace_lines(self.root, trace_date)


class LocalProfileService:
    def __init__(self, root: Path) -> None:
        self.root = root

    def create_default(self) -> Path:
        return create_default_profile(self.root)

    def load(self) -> ProjectProfile:
        return load_project_profile(self.root)

    def set_active(self, profile_name: str) -> ProjectProfile:
        return set_active_profile(self.create_default(), profile_name)

    def validate(self, known_skills: set[str] | None = None) -> ProfileValidation:
        return validate_profile(self.create_default(), known_skills=known_skills)

    def resolve_memory_project(self, project: str | None = None) -> str:
        if project:
            return project
        return self.load().active.memory_project


class LocalDoctorService:
    def __init__(self, root: Path) -> None:
        self.root = root

    def run(self) -> DoctorReport:
        return run_doctor(self.root)


class LocalRefinerService:
    def analyze_trace(self, trace_path: Path) -> str:
        return (
            "TODO: RefinerService is a Phase 2 service boundary stub for future "
            f"Continual Harness trace analysis integrations: {trace_path}"
        )
