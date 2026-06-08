import json
from datetime import UTC, datetime

from agentos.logging.traces import TraceEventType, TraceLogger, list_trace_files, read_trace_events


def test_trace_logger_writes_daily_jsonl(tmp_path):
    logger = TraceLogger(tmp_path)

    event = logger.log_event(
        TraceEventType.MEMORY_ADDED,
        command="memory.add",
        status="ok",
        project="demo",
        payload={"memory_id": 1},
    )

    trace_path = tmp_path / ".agentos" / "traces" / f"{datetime.now(UTC).date()}.jsonl"
    lines = trace_path.read_text(encoding="utf-8").splitlines()
    payload = json.loads(lines[0])

    assert event.event_type == "memory_added"
    assert payload["event_type"] == "memory_added"
    assert payload["event"] == "memory_added"
    assert payload["command"] == "memory.add"
    assert payload["status"] == "ok"
    assert payload["project"] == "demo"
    assert payload["payload"] == {"memory_id": 1}
    assert payload["error"] is None
    assert "id" in payload
    assert "timestamp" in payload


def test_trace_jsonl_is_valid_and_readable(tmp_path):
    logger = TraceLogger(tmp_path)
    logger.log_event(TraceEventType.COMMAND_STARTED, command="doctor", status="started")
    logger.log_event(TraceEventType.COMMAND_COMPLETED, command="doctor", status="ok")

    dates = list_trace_files(tmp_path)
    events = read_trace_events(tmp_path, dates[0])

    assert len(events) == 2
    assert [event.event_type for event in events] == ["command_started", "command_completed"]


def test_trace_logger_redacts_sensitive_values(tmp_path):
    logger = TraceLogger(tmp_path)

    logger.log_event(
        TraceEventType.POLICY_CHECKED,
        command="policies.check",
        status="block",
        payload={
            "path": ".env",
            "nested": {"api_key": "sk-secret-value"},
            "safe": "README.md",
        },
        error="attempted to inspect credentials/token.txt",
    )

    trace_path = tmp_path / ".agentos" / "traces" / f"{datetime.now(UTC).date()}.jsonl"
    payload = json.loads(trace_path.read_text(encoding="utf-8").splitlines()[0])

    assert payload["payload"]["path"] == "[REDACTED]"
    assert payload["payload"]["nested"]["api_key"] == "[REDACTED]"
    assert payload["payload"]["safe"] == "README.md"
    assert payload["error"] == "[REDACTED]"
