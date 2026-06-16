from __future__ import annotations

import json
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

REDACTED = "[REDACTED]"
SENSITIVE_TERMS = [
    ".env",
    ".pem",
    ".key",
    ".ssh",
    "id_rsa",
    "id_ed25519",
    "private_key",
    "credentials",
    "secrets",
    "token",
    "api_key",
    "banking",
    "medical_records",
    "sk-",
]


class TraceEventType(StrEnum):
    COMMAND_STARTED = "command_started"
    COMMAND_COMPLETED = "command_completed"
    COMMAND_FAILED = "command_failed"
    MEMORY_ADDED = "memory_added"
    MEMORY_SEARCHED = "memory_searched"
    MEMORY_DELETED = "memory_deleted"
    SDD_CREATED = "sdd_created"
    SDD_PHASE_ADVANCED = "sdd_phase_advanced"
    SKILL_SCAN_COMPLETED = "skill_scan_completed"
    POLICY_VIOLATION = "policy_violation"
    POLICY_CHECKED = "policy_checked"
    MODEL_REQUEST_STARTED = "model_request_started"
    MODEL_REQUEST_COMPLETED = "model_request_completed"
    MODEL_REQUEST_FAILED = "model_request_failed"
    MODEL_USAGE_UPDATED = "model_usage_updated"
    AGENT_STARTED = "agent_started"
    AGENT_STOPPED = "agent_stopped"
    AGENT_STATE_CLEARED = "agent_state_cleared"
    INTERACTIVE_MESSAGE_SENT = "interactive_message_sent"
    INTERACTIVE_MESSAGE_RECEIVED = "interactive_message_received"
    CONTEXT_WARNING = "context_warning"
    CONTEXT_COMPACTED = "context_compacted"
    STREAM_STARTED = "stream_started"
    STREAM_DELTA_RECEIVED = "stream_delta_received"
    STREAM_COMPLETED = "stream_completed"
    STREAM_FAILED = "stream_failed"
    RETRIEVAL_REQUESTED = "retrieval_requested"
    RETRIEVAL_CONTEXT_BUILT = "retrieval_context_built"
    RETRIEVAL_CONTEXT_SENT = "retrieval_context_sent"
    RETRIEVAL_DRY_RUN = "retrieval_dry_run"


class TraceEvent(BaseModel):
    id: str
    timestamp: str
    event_type: TraceEventType
    command: str
    status: str
    project: str | None = None
    payload: dict[str, object]
    error: str | None = None

    @property
    def event(self) -> str:
        return self.event_type.value

    def jsonl_payload(self) -> dict[str, object]:
        payload = self.model_dump(mode="json")
        payload["event"] = self.event_type.value
        return payload


class TraceLogger:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.traces_dir = root / ".agentos" / "traces"
        self.traces_dir.mkdir(parents=True, exist_ok=True)

    def log_event(
        self,
        event_type: TraceEventType | str,
        command: str | dict[str, object] = "",
        status: str = "ok",
        project: str | None = None,
        payload: dict[str, object] | None = None,
        error: str | None = None,
    ) -> TraceEvent:
        if isinstance(command, dict) and payload is None:
            payload = command
            command = str(payload.get("command", ""))

        event = TraceEvent(
            id=uuid4().hex,
            timestamp=datetime.now(UTC).isoformat(),
            event_type=TraceEventType(str(event_type)),
            command=str(_redact(command)),
            status=str(_redact(status)),
            project=None if project is None else str(_redact(project)),
            payload=_redact_payload(payload or {}),
            error=None if error is None else str(_redact(error)),
        )
        path = self.path_for_date(datetime.fromisoformat(event.timestamp).date())
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event.jsonl_payload(), sort_keys=True) + "\n")
        return event

    def path_for_date(self, trace_date: date | str) -> Path:
        date_value = trace_date if isinstance(trace_date, str) else trace_date.isoformat()
        return self.traces_dir / f"{date_value}.jsonl"


def list_trace_files(root: Path) -> list[str]:
    traces_dir = root / ".agentos" / "traces"
    if not traces_dir.exists():
        return []
    return sorted(path.stem for path in traces_dir.glob("*.jsonl"))


def read_trace_events(root: Path, trace_date: str) -> list[TraceEvent]:
    path = TraceLogger(root).path_for_date(trace_date)
    if not path.exists():
        return []
    return [
        _event_from_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def tail_trace_events(root: Path, limit: int = 20) -> list[TraceEvent]:
    dates = list_trace_files(root)
    events: list[TraceEvent] = []
    for trace_date in dates:
        events.extend(read_trace_events(root, trace_date))
    return events[-limit:]


def export_trace_lines(root: Path, trace_date: str | None = None) -> list[str]:
    dates = [trace_date] if trace_date else list_trace_files(root)
    lines: list[str] = []
    logger = TraceLogger(root)
    for date_value in dates:
        path = logger.path_for_date(date_value)
        if path.exists():
            lines.extend(line for line in path.read_text(encoding="utf-8").splitlines() if line)
    return lines


def _event_from_json(line: str) -> TraceEvent:
    data = json.loads(line)
    if "event_type" not in data and "event" in data:
        data["event_type"] = data["event"]
    if data.get("event_type") == "search_performed":
        data["event_type"] = TraceEventType.MEMORY_SEARCHED.value
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
    data.setdefault("id", uuid4().hex)
    data.setdefault("timestamp", datetime.now(UTC).isoformat())
    data.setdefault("command", str(payload.get("command", "")))
    data.setdefault("status", "ok")
    data.setdefault("project", payload.get("project"))
    data.setdefault("payload", payload)
    data.setdefault("error", None)
    data.pop("event", None)
    return TraceEvent(**data)


def _redact_payload(payload: dict[str, object]) -> dict[str, object]:
    return {key: _redact_by_key(key, value) for key, value in payload.items()}


def _redact_by_key(key: str, value: object) -> object:
    if _is_sensitive_text(key):
        return REDACTED
    return _redact(value)


def _redact(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _redact_by_key(str(key), item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return [_redact(item) for item in value]
    if isinstance(value, str) and _is_sensitive_text(value):
        return REDACTED
    return value


def _is_sensitive_text(value: str) -> bool:
    normalized = value.replace("\\", "/").lower()
    return any(term in normalized for term in SENSITIVE_TERMS)
