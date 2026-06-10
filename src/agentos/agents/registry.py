from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from agentos.agents.schemas import AgentKind, AgentRecord, AgentRuntimeState, AgentStatus
from agentos.models.routing import effective_effort

ACTIVE_STATUSES = {AgentStatus.RUNNING, AgentStatus.WAITING, AgentStatus.IDLE}


class AgentRuntimeRegistry:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.path = root / ".agentos" / "agents" / "runtime-state.json"

    def list_agents(self) -> list[AgentRecord]:
        return self._sort_agents(self._read_state().agents)

    def start_agent(
        self,
        *,
        name: str,
        role: str,
        current_task: str,
        model_profile: str,
        effort: str | None = None,
        kind: AgentKind | str = AgentKind.AGENT,
        parent_id: str | None = None,
    ) -> AgentRecord:
        state = self._read_state()
        now = _now()
        effort_value = effective_effort(self.root, "coding", effort)
        record = AgentRecord(
            id=uuid4().hex,
            name=name,
            role=role,
            kind=AgentKind(str(kind)),
            status=AgentStatus.RUNNING,
            model_profile=model_profile,
            effort=effort_value,
            parent_id=parent_id,
            current_task=current_task,
            started_at=now,
            updated_at=now,
        )
        state.agents.append(record)
        self._write_state(state)
        return record

    def stop_agent(self, agent_id: str, status: AgentStatus = AgentStatus.COMPLETED) -> AgentRecord:
        state = self._read_state()
        updated_agents: list[AgentRecord] = []
        stopped: AgentRecord | None = None
        for agent in state.agents:
            if agent.id == agent_id:
                stopped = agent.model_copy(update={"status": status, "updated_at": _now()})
                updated_agents.append(stopped)
            else:
                updated_agents.append(agent)
        if stopped is None:
            raise KeyError(f"Unknown agent id: {agent_id}")
        self._write_state(AgentRuntimeState(agents=updated_agents))
        return stopped

    def clear(self, *, confirm: bool = False) -> None:
        if not confirm:
            raise ValueError("Agent runtime clear requires --confirm.")
        self._write_state(AgentRuntimeState())

    def _read_state(self) -> AgentRuntimeState:
        if not self.path.exists():
            return AgentRuntimeState()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return AgentRuntimeState()
        agents = data.get("agents") if isinstance(data, dict) else []
        if not isinstance(agents, list):
            return AgentRuntimeState()
        return AgentRuntimeState(
            agents=[AgentRecord(**agent) for agent in agents if isinstance(agent, dict)]
        )

    def _write_state(self, state: AgentRuntimeState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = state.model_dump(mode="json")
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _sort_agents(self, agents: list[AgentRecord]) -> list[AgentRecord]:
        return sorted(
            agents,
            key=lambda agent: (
                0 if agent.status in ACTIVE_STATUSES else 1,
                agent.updated_at,
            ),
            reverse=False,
        )


def _now() -> str:
    return datetime.now(UTC).isoformat()
