from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from agentos.usage.schemas import UsageEvent, UsageSummary


class UsageStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.db_path = root / ".agentos" / "usage" / "usage.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def record_event(
        self,
        *,
        session_id: str,
        project: str,
        profile: str,
        provider: str,
        model: str,
        effort: str,
        agent_id: str | None,
        command: str,
        input_tokens: int,
        output_tokens: int,
        estimated_cost_usd: float | None,
        context_used_percent: float | None,
        timestamp: str | None = None,
    ) -> UsageEvent:
        if input_tokens < 0 or output_tokens < 0:
            raise ValueError("Token counts must be non-negative.")
        event = UsageEvent(
            id=uuid4().hex,
            timestamp=timestamp or datetime.now(UTC).isoformat(),
            session_id=session_id,
            project=project,
            profile=profile,
            provider=provider,
            model=model,
            effort=effort,
            agent_id=agent_id,
            command=command,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            estimated_cost_usd=estimated_cost_usd,
            context_used_percent=context_used_percent,
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO usage_events (
                    id, timestamp, session_id, project, profile, provider, model,
                    effort, agent_id, command, input_tokens, output_tokens,
                    total_tokens, estimated_cost_usd, context_used_percent
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.timestamp,
                    event.session_id,
                    event.project,
                    event.profile,
                    event.provider,
                    event.model,
                    event.effort,
                    event.agent_id,
                    event.command,
                    event.input_tokens,
                    event.output_tokens,
                    event.total_tokens,
                    event.estimated_cost_usd,
                    event.context_used_percent,
                ),
            )
            self._refresh_summaries(conn)
        return event

    def events(self) -> list[UsageEvent]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, timestamp, session_id, project, profile, provider, model,
                       effort, agent_id, command, input_tokens, output_tokens,
                       total_tokens, estimated_cost_usd, context_used_percent
                FROM usage_events
                ORDER BY timestamp, id
                """
            ).fetchall()
        return [_event_from_row(row) for row in rows]

    def summary(self) -> UsageSummary:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*), COALESCE(SUM(input_tokens), 0),
                       COALESCE(SUM(output_tokens), 0),
                       COALESCE(SUM(total_tokens), 0),
                       CASE
                         WHEN COUNT(*) = COUNT(estimated_cost_usd)
                         THEN SUM(estimated_cost_usd)
                         ELSE NULL
                       END
                FROM usage_events
                """
            ).fetchone()
        return _summary_from_aggregate("total", row)

    def daily_summary(self, usage_date: str | None = None) -> list[UsageSummary]:
        where = ""
        params: tuple[str, ...] = ()
        if usage_date is not None:
            where = "WHERE usage_date = ?"
            params = (usage_date,)
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT usage_date, project, profile, event_count, input_tokens,
                       output_tokens, total_tokens, estimated_cost_usd
                FROM usage_daily_summary
                {where}
                ORDER BY usage_date DESC, project, profile
                """,
                params,
            ).fetchall()
        return [
            UsageSummary(
                key=f"{row['usage_date']}:{row['project']}:{row['profile']}",
                usage_date=row["usage_date"],
                project=row["project"],
                profile=row["profile"],
                event_count=row["event_count"],
                input_tokens=row["input_tokens"],
                output_tokens=row["output_tokens"],
                total_tokens=row["total_tokens"],
                estimated_cost_usd=row["estimated_cost_usd"],
            )
            for row in rows
        ]

    def model_summary(self) -> list[UsageSummary]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT provider, model, profile, event_count, input_tokens,
                       output_tokens, total_tokens, estimated_cost_usd
                FROM usage_model_summary
                ORDER BY total_tokens DESC, provider, model
                """
            ).fetchall()
        return [
            UsageSummary(
                key=f"{row['provider']}:{row['model']}:{row['profile']}",
                provider=row["provider"],
                model=row["model"],
                profile=row["profile"],
                event_count=row["event_count"],
                input_tokens=row["input_tokens"],
                output_tokens=row["output_tokens"],
                total_tokens=row["total_tokens"],
                estimated_cost_usd=row["estimated_cost_usd"],
            )
            for row in rows
        ]

    def agent_summary(self) -> list[UsageSummary]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT agent_id, event_count, input_tokens, output_tokens,
                       total_tokens, estimated_cost_usd
                FROM usage_agent_summary
                ORDER BY total_tokens DESC, agent_id
                """
            ).fetchall()
        return [
            UsageSummary(
                key=row["agent_id"],
                agent_id=row["agent_id"],
                event_count=row["event_count"],
                input_tokens=row["input_tokens"],
                output_tokens=row["output_tokens"],
                total_tokens=row["total_tokens"],
                estimated_cost_usd=row["estimated_cost_usd"],
            )
            for row in rows
        ]

    def session_summary(self, session_id: str | None = None) -> UsageSummary:
        session = session_id or self.latest_session_id()
        if session is None:
            return UsageSummary(key="session", session_id=None)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*), COALESCE(SUM(input_tokens), 0),
                       COALESCE(SUM(output_tokens), 0),
                       COALESCE(SUM(total_tokens), 0),
                       CASE
                         WHEN COUNT(*) = COUNT(estimated_cost_usd)
                         THEN SUM(estimated_cost_usd)
                         ELSE NULL
                       END
                FROM usage_events
                WHERE session_id = ?
                """,
                (session,),
            ).fetchone()
        summary = _summary_from_aggregate("session", row)
        summary.session_id = session
        return summary

    def today_summary(self) -> UsageSummary:
        today = datetime.now(UTC).date().isoformat()
        summaries = self.daily_summary(today)
        if not summaries:
            return UsageSummary(key=today, usage_date=today)
        if len(summaries) == 1:
            return summaries[0]
        cost = _sum_costs([summary.estimated_cost_usd for summary in summaries])
        return UsageSummary(
            key=today,
            usage_date=today,
            event_count=sum(summary.event_count for summary in summaries),
            input_tokens=sum(summary.input_tokens for summary in summaries),
            output_tokens=sum(summary.output_tokens for summary in summaries),
            total_tokens=sum(summary.total_tokens for summary in summaries),
            estimated_cost_usd=cost,
        )

    def latest_session_id(self) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT session_id
                FROM usage_events
                ORDER BY timestamp DESC, id DESC
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            return None
        return str(row["session_id"])

    def export_json(self) -> str:
        payload = {
            "events": [event.model_dump(mode="json") for event in self.events()],
            "daily_summary": [
                summary.model_dump(mode="json") for summary in self.daily_summary()
            ],
            "model_summary": [
                summary.model_dump(mode="json") for summary in self.model_summary()
            ],
            "agent_summary": [
                summary.model_dump(mode="json") for summary in self.agent_summary()
            ],
        }
        return json.dumps(payload, indent=2) + "\n"

    def reset(self, *, confirm: bool = False) -> None:
        if not confirm:
            raise ValueError("Usage reset requires --confirm.")
        with self._connect() as conn:
            conn.execute("DELETE FROM usage_events")
            conn.execute("DELETE FROM usage_daily_summary")
            conn.execute("DELETE FROM usage_model_summary")
            conn.execute("DELETE FROM usage_agent_summary")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS usage_events (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    project TEXT NOT NULL,
                    profile TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    effort TEXT NOT NULL,
                    agent_id TEXT,
                    command TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    estimated_cost_usd REAL,
                    context_used_percent REAL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS usage_daily_summary (
                    usage_date TEXT NOT NULL,
                    project TEXT NOT NULL,
                    profile TEXT NOT NULL,
                    event_count INTEGER NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    estimated_cost_usd REAL,
                    PRIMARY KEY (usage_date, project, profile)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS usage_model_summary (
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    profile TEXT NOT NULL,
                    event_count INTEGER NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    estimated_cost_usd REAL,
                    PRIMARY KEY (provider, model, profile)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS usage_agent_summary (
                    agent_id TEXT PRIMARY KEY,
                    event_count INTEGER NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    estimated_cost_usd REAL
                )
                """
            )

    def _refresh_summaries(self, conn: sqlite3.Connection) -> None:
        conn.execute("DELETE FROM usage_daily_summary")
        conn.execute(
            """
            INSERT INTO usage_daily_summary (
                usage_date, project, profile, event_count, input_tokens,
                output_tokens, total_tokens, estimated_cost_usd
            )
            SELECT substr(timestamp, 1, 10), project, profile, COUNT(*),
                   SUM(input_tokens), SUM(output_tokens), SUM(total_tokens),
                   CASE
                     WHEN COUNT(*) = COUNT(estimated_cost_usd)
                     THEN SUM(estimated_cost_usd)
                     ELSE NULL
                   END
            FROM usage_events
            GROUP BY substr(timestamp, 1, 10), project, profile
            """
        )
        conn.execute("DELETE FROM usage_model_summary")
        conn.execute(
            """
            INSERT INTO usage_model_summary (
                provider, model, profile, event_count, input_tokens,
                output_tokens, total_tokens, estimated_cost_usd
            )
            SELECT provider, model, profile, COUNT(*), SUM(input_tokens),
                   SUM(output_tokens), SUM(total_tokens),
                   CASE
                     WHEN COUNT(*) = COUNT(estimated_cost_usd)
                     THEN SUM(estimated_cost_usd)
                     ELSE NULL
                   END
            FROM usage_events
            GROUP BY provider, model, profile
            """
        )
        conn.execute("DELETE FROM usage_agent_summary")
        conn.execute(
            """
            INSERT INTO usage_agent_summary (
                agent_id, event_count, input_tokens, output_tokens,
                total_tokens, estimated_cost_usd
            )
            SELECT agent_id, COUNT(*), SUM(input_tokens), SUM(output_tokens),
                   SUM(total_tokens),
                   CASE
                     WHEN COUNT(*) = COUNT(estimated_cost_usd)
                     THEN SUM(estimated_cost_usd)
                     ELSE NULL
                   END
            FROM usage_events
            WHERE agent_id IS NOT NULL AND agent_id != ''
            GROUP BY agent_id
            """
        )


def _event_from_row(row: sqlite3.Row) -> UsageEvent:
    return UsageEvent(
        id=row["id"],
        timestamp=row["timestamp"],
        session_id=row["session_id"],
        project=row["project"],
        profile=row["profile"],
        provider=row["provider"],
        model=row["model"],
        effort=row["effort"],
        agent_id=row["agent_id"],
        command=row["command"],
        input_tokens=row["input_tokens"],
        output_tokens=row["output_tokens"],
        total_tokens=row["total_tokens"],
        estimated_cost_usd=row["estimated_cost_usd"],
        context_used_percent=row["context_used_percent"],
    )


def _summary_from_aggregate(key: str, row: sqlite3.Row) -> UsageSummary:
    return UsageSummary(
        key=key,
        event_count=int(row[0] or 0),
        input_tokens=int(row[1] or 0),
        output_tokens=int(row[2] or 0),
        total_tokens=int(row[3] or 0),
        estimated_cost_usd=row[4],
    )


def _sum_costs(costs: list[float | None]) -> float | None:
    if any(cost is None for cost in costs):
        return None
    return round(sum(float(cost) for cost in costs), 8)
