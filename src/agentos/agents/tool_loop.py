from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from agentos.agents.planner import AgentPlanner
from agentos.logging.traces import TraceEventType, TraceLogger
from agentos.tools.builtin_tools import create_builtin_tool_registry
from agentos.tools.executor import ToolExecutor
from agentos.tools.registry import ToolRegistry
from agentos.tools.schemas import ToolExecutionContext, ToolResult

DEFAULT_MAX_TOOL_CALLS_PER_RUN = 5


class AgentRunResult(BaseModel):
    name: str
    role: str
    task: str
    status: str
    final_answer: str
    steps: int
    tool_results: list[ToolResult] = Field(default_factory=list)


class AgentToolLoop:
    def __init__(
        self,
        root: Path,
        *,
        registry: ToolRegistry | None = None,
        planner: AgentPlanner | None = None,
        trace: TraceLogger | None = None,
    ) -> None:
        self.root = root
        self.registry = registry or create_builtin_tool_registry()
        self.planner = planner or AgentPlanner(root)
        self.trace = trace or TraceLogger(root)
        self.executor = ToolExecutor(root, self.registry, self.trace)

    def run(
        self,
        *,
        name: str,
        role: str,
        task: str,
        max_steps: int = DEFAULT_MAX_TOOL_CALLS_PER_RUN,
        approvals: set[str] | None = None,
    ) -> AgentRunResult:
        self.trace.log_event(
            TraceEventType.AGENT_RUN_STARTED,
            command="agents.run",
            status="started",
            payload={"name": name, "role": role, "max_steps": max_steps},
        )
        context = ToolExecutionContext(approvals=approvals or set())
        results: list[ToolResult] = []
        final_answer = ""
        try:
            for step in range(1, max_steps + 1):
                plan = self.planner.next_step(
                    task=task,
                    role=role,
                    tools=sorted(self.registry.names()),
                    previous_results=results,
                    step=step,
                )
                if plan.final_answer and not plan.tool_calls:
                    final_answer = plan.final_answer
                    return self._completed(name, role, task, final_answer, step, results)
                if not plan.tool_calls:
                    final_answer = "Agent stopped without tool calls."
                    return self._completed(name, role, task, final_answer, step, results)
                for call in plan.tool_calls:
                    if len(results) >= max_steps:
                        final_answer = "Stopped after max steps."
                        return self._completed(name, role, task, final_answer, step, results)
                    results.append(self.executor.execute(call, context))
            final_answer = "Stopped after max steps."
            return self._completed(name, role, task, final_answer, max_steps, results)
        except Exception as error:
            self.trace.log_event(
                TraceEventType.AGENT_RUN_FAILED,
                command="agents.run",
                status="failed",
                payload={"name": name, "role": role},
                error=str(error),
            )
            return AgentRunResult(
                name=name,
                role=role,
                task=task,
                status="failed",
                final_answer=str(error),
                steps=len(results),
                tool_results=results,
            )

    def _completed(
        self,
        name: str,
        role: str,
        task: str,
        final_answer: str,
        steps: int,
        results: list[ToolResult],
    ) -> AgentRunResult:
        self.trace.log_event(
            TraceEventType.AGENT_RUN_COMPLETED,
            command="agents.run",
            status="completed",
            payload={"name": name, "role": role, "steps": steps, "tool_results": len(results)},
        )
        return AgentRunResult(
            name=name,
            role=role,
            task=task,
            status="completed",
            final_answer=final_answer,
            steps=steps,
            tool_results=results,
        )
