from datetime import UTC, datetime

import pytest

from agentos.agents.registry import AgentRuntimeRegistry
from agentos.agents.schemas import AgentKind, AgentStatus


def test_agent_registry_creates_runtime_state_file(tmp_path):
    registry = AgentRuntimeRegistry(tmp_path)

    agent = registry.start_agent(
        name="Planner",
        role="planning",
        current_task="Plan next local change",
        model_profile="local-stub",
    )

    state_path = tmp_path / ".agentos" / "agents" / "runtime-state.json"
    loaded = registry.list_agents()

    assert state_path.exists()
    assert agent.status == AgentStatus.RUNNING
    assert loaded[0].name == "Planner"
    assert loaded[0].model_profile == "local-stub"
    assert loaded[0].input_tokens == 0
    assert loaded[0].output_tokens == 0
    assert loaded[0].estimated_cost_usd is None


def test_start_list_stop_agent(tmp_path):
    registry = AgentRuntimeRegistry(tmp_path)
    agent = registry.start_agent(
        name="Worker",
        role="implementation",
        current_task="Track local runtime state",
        model_profile="local-stub",
        effort="low",
    )

    stopped = registry.stop_agent(agent.id)
    agents = registry.list_agents()

    assert stopped.status == AgentStatus.COMPLETED
    assert agents[0].id == agent.id
    assert agents[0].status == AgentStatus.COMPLETED
    assert datetime.fromisoformat(agents[0].updated_at) >= datetime.fromisoformat(
        agent.updated_at
    )


def test_subagent_parent_relationship(tmp_path):
    registry = AgentRuntimeRegistry(tmp_path)
    parent = registry.start_agent(
        name="Lead",
        role="coordination",
        current_task="Coordinate analysis",
        model_profile="local-stub",
    )
    subagent = registry.start_agent(
        name="Researcher",
        role="subtask research",
        current_task="Inspect docs",
        model_profile="local-stub",
        kind=AgentKind.SUBAGENT,
        parent_id=parent.id,
    )

    loaded = registry.list_agents()

    assert subagent.kind == AgentKind.SUBAGENT
    assert loaded[1].parent_id == parent.id


def test_clear_requires_confirm(tmp_path):
    registry = AgentRuntimeRegistry(tmp_path)
    registry.start_agent(
        name="Temp",
        role="testing",
        current_task="Exercise confirm guard",
        model_profile="local-stub",
    )

    with pytest.raises(ValueError, match="--confirm"):
        registry.clear(confirm=False)

    registry.clear(confirm=True)

    assert registry.list_agents() == []


def test_active_agents_are_listed_first(tmp_path):
    registry = AgentRuntimeRegistry(tmp_path)
    completed = registry.start_agent(
        name="Done",
        role="finished",
        current_task="Completed work",
        model_profile="local-stub",
    )
    registry.stop_agent(completed.id)
    running = registry.start_agent(
        name="Active",
        role="runtime",
        current_task="Still running",
        model_profile="local-stub",
    )

    agents = registry.list_agents()

    assert agents[0].id == running.id
    assert agents[0].status == AgentStatus.RUNNING


def test_agent_start_does_not_execute_autonomous_work(tmp_path):
    registry = AgentRuntimeRegistry(tmp_path)

    agent = registry.start_agent(
        name="No Autonomy",
        role="tracking only",
        current_task="Do not execute anything",
        model_profile="openrouter-auto",
    )

    assert agent.status == AgentStatus.RUNNING
    assert agent.started_at.endswith("+00:00")
    assert datetime.fromisoformat(agent.started_at).tzinfo == UTC
    assert agent.input_tokens == 0
    assert agent.output_tokens == 0
    assert agent.estimated_cost_usd is None
