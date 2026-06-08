import json
from datetime import UTC, datetime

from agentos.logging.traces import TraceLogger


def test_trace_logger_writes_daily_jsonl(tmp_path):
    logger = TraceLogger(tmp_path)

    event = logger.log_event("memory_added", {"memory_id": 1, "project": "demo"})

    trace_path = tmp_path / ".agentos" / "traces" / f"{datetime.now(UTC).date()}.jsonl"
    lines = trace_path.read_text(encoding="utf-8").splitlines()
    payload = json.loads(lines[0])

    assert event.event == "memory_added"
    assert payload["event"] == "memory_added"
    assert payload["payload"] == {"memory_id": 1, "project": "demo"}
    assert "timestamp" in payload
