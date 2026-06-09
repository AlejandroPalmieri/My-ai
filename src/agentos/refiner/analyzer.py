from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from agentos.logging.traces import TraceEvent, TraceEventType, tail_trace_events


@dataclass(frozen=True)
class RefinerFinding:
    finding_type: str
    severity: str
    subject: str
    count: int
    detail: str
    recommendation: str

    def to_dict(self) -> dict[str, object]:
        return {
            "finding_type": self.finding_type,
            "severity": self.severity,
            "subject": self.subject,
            "count": self.count,
            "detail": self.detail,
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True)
class RefinerAnalysis:
    generated_at: str
    events_scanned: int
    findings: list[RefinerFinding]

    @property
    def has_findings(self) -> bool:
        return bool(self.findings)

    def finding_by_type(self, finding_type: str) -> RefinerFinding | None:
        return next(
            (finding for finding in self.findings if finding.finding_type == finding_type),
            None,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "generated_at": self.generated_at,
            "events_scanned": self.events_scanned,
            "findings": [finding.to_dict() for finding in self.findings],
        }


class TraceRefiner:
    """Analyzes local traces and proposes improvements without changing files."""

    def __init__(self, root: Path, limit: int = 200) -> None:
        self.root = root
        self.limit = limit

    def analyze(self) -> RefinerAnalysis:
        events = tail_trace_events(self.root, limit=self.limit)
        findings = [
            *self._repeated_command_failures(events),
            *self._frequent_policy_violations(events),
            *self._failed_searches(events),
        ]
        return RefinerAnalysis(
            generated_at=datetime.now(UTC).isoformat(),
            events_scanned=len(events),
            findings=findings,
        )

    def _repeated_command_failures(self, events: list[TraceEvent]) -> list[RefinerFinding]:
        failures = Counter(
            event.command or "unknown"
            for event in events
            if event.event_type == TraceEventType.COMMAND_FAILED
        )
        return [
            RefinerFinding(
                finding_type="repeated_command_failures",
                severity="warn",
                subject=command,
                count=count,
                detail=f"{command} failed {count} times in recent traces.",
                recommendation=(
                    "Review command error handling, CLI validation, and documentation "
                    "for this path."
                ),
            )
            for command, count in failures.items()
            if count >= 2
        ]

    def _frequent_policy_violations(self, events: list[TraceEvent]) -> list[RefinerFinding]:
        violations = Counter(
            str(event.payload.get("matched_rule") or event.command or "unknown")
            for event in events
            if event.event_type == TraceEventType.POLICY_VIOLATION
        )
        return [
            RefinerFinding(
                finding_type="frequent_policy_violations",
                severity="warn",
                subject=subject,
                count=count,
                detail=f"Policy rule {subject} was violated {count} times.",
                recommendation=(
                    "Clarify policy docs or add safer workflow examples for this "
                    "repeated violation."
                ),
            )
            for subject, count in violations.items()
            if count >= 2
        ]

    def _failed_searches(self, events: list[TraceEvent]) -> list[RefinerFinding]:
        searches = Counter(
            str(event.payload.get("query") or event.command or "unknown")
            for event in events
            if event.event_type == TraceEventType.MEMORY_SEARCHED
            and int(event.payload.get("result_count", 1) or 0) == 0
        )
        return [
            RefinerFinding(
                finding_type="failed_searches",
                severity="info",
                subject=query,
                count=count,
                detail=f"Search query {query!r} returned no results {count} time(s).",
                recommendation=(
                    "Consider adding memories, improving tags, or documenting better search terms."
                ),
            )
            for query, count in searches.items()
        ]
