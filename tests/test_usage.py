import json
import sqlite3

import pytest

from agentos.usage.store import UsageStore


def test_usage_event_insert_does_not_store_prompt_body(tmp_path):
    store = UsageStore(tmp_path)

    event = store.record_event(
        session_id="session-1",
        project="default",
        profile="default",
        provider="local",
        model="local-stub",
        effort="medium",
        agent_id=None,
        command="chat.once",
        input_tokens=12,
        output_tokens=8,
        estimated_cost_usd=0.001,
        context_used_percent=4.2,
    )

    assert event.id
    assert event.total_tokens == 20
    assert store.db_path == tmp_path / ".agentos" / "usage" / "usage.db"
    with sqlite3.connect(store.db_path) as conn:
        columns = [row[1] for row in conn.execute("PRAGMA table_info(usage_events)")]
        rows = conn.execute("SELECT command, total_tokens FROM usage_events").fetchall()

    assert "prompt" not in columns
    assert "message" not in columns
    assert rows == [("chat.once", 20)]


def test_daily_summary(tmp_path):
    store = UsageStore(tmp_path)
    store.record_event(
        session_id="session-1",
        project="default",
        profile="default",
        provider="local",
        model="local-stub",
        effort="medium",
        agent_id=None,
        command="chat.once",
        input_tokens=10,
        output_tokens=5,
        estimated_cost_usd=0.01,
        context_used_percent=1.0,
        timestamp="2026-06-09T10:00:00+00:00",
    )
    store.record_event(
        session_id="session-2",
        project="default",
        profile="default",
        provider="local",
        model="local-stub",
        effort="high",
        agent_id=None,
        command="chat.once",
        input_tokens=20,
        output_tokens=10,
        estimated_cost_usd=0.02,
        context_used_percent=2.0,
        timestamp="2026-06-09T11:00:00+00:00",
    )

    summary = store.daily_summary("2026-06-09")

    assert len(summary) == 1
    assert summary[0].total_tokens == 45
    assert summary[0].estimated_cost_usd == 0.03
    assert summary[0].event_count == 2


def test_by_model_summary(tmp_path):
    store = UsageStore(tmp_path)
    store.record_event(
        session_id="session-1",
        project="default",
        profile="default",
        provider="local",
        model="local-stub",
        effort="medium",
        agent_id=None,
        command="chat.once",
        input_tokens=10,
        output_tokens=5,
        estimated_cost_usd=None,
        context_used_percent=1.0,
    )

    summary = store.model_summary()

    assert summary[0].provider == "local"
    assert summary[0].model == "local-stub"
    assert summary[0].total_tokens == 15
    assert summary[0].estimated_cost_usd is None


def test_by_agent_summary(tmp_path):
    store = UsageStore(tmp_path)
    store.record_event(
        session_id="session-1",
        project="default",
        profile="default",
        provider="local",
        model="local-stub",
        effort="medium",
        agent_id="agent-1",
        command="chat.once",
        input_tokens=30,
        output_tokens=20,
        estimated_cost_usd=0.05,
        context_used_percent=5.0,
    )

    summary = store.agent_summary()

    assert summary[0].agent_id == "agent-1"
    assert summary[0].input_tokens == 30
    assert summary[0].output_tokens == 20
    assert summary[0].estimated_cost_usd == 0.05


def test_reset_requires_confirm(tmp_path):
    store = UsageStore(tmp_path)
    store.record_event(
        session_id="session-1",
        project="default",
        profile="default",
        provider="local",
        model="local-stub",
        effort="medium",
        agent_id=None,
        command="chat.once",
        input_tokens=1,
        output_tokens=1,
        estimated_cost_usd=0.0,
        context_used_percent=1.0,
    )

    with pytest.raises(ValueError, match="--confirm"):
        store.reset(confirm=False)

    store.reset(confirm=True)

    assert store.events() == []


def test_usage_export_json(tmp_path):
    store = UsageStore(tmp_path)
    store.record_event(
        session_id="session-1",
        project="default",
        profile="default",
        provider="local",
        model="local-stub",
        effort="medium",
        agent_id=None,
        command="chat.once",
        input_tokens=3,
        output_tokens=2,
        estimated_cost_usd=0.0,
        context_used_percent=1.0,
    )

    payload = json.loads(store.export_json())

    assert payload["events"][0]["total_tokens"] == 5
    assert payload["events"][0].get("prompt") is None
