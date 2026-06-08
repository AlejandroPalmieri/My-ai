from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

TraceEventName = Literal[
    "command_started",
    "command_completed",
    "memory_added",
    "search_performed",
    "policy_violation",
    "sdd_created",
]


class TraceEvent(BaseModel):
    timestamp: str
    event: TraceEventName
    payload: dict[str, object]


class TraceLogger:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.traces_dir = root / ".agentos" / "traces"
        self.traces_dir.mkdir(parents=True, exist_ok=True)

    def log_event(self, event: TraceEventName, payload: dict[str, object]) -> TraceEvent:
        trace_event = TraceEvent(
            timestamp=datetime.now(UTC).isoformat(),
            event=event,
            payload=payload,
        )
        path = self.traces_dir / f"{datetime.now(UTC).date()}.jsonl"
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(trace_event.model_dump(), sort_keys=True) + "\n")
        return trace_event
