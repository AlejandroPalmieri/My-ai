from __future__ import annotations

import json
from pathlib import Path

from agentos.models.client import chat_once
from agentos.tools.schemas import ToolCall, ToolProtocolMessage, ToolResult

PROTOCOL_INSTRUCTIONS = """
AGENTOS_TOOL_PROTOCOL
Return only JSON using this shape:
{"tool_calls":[{"name":"tool_name","arguments":{}}],"final_answer":null}
or {"tool_calls":[],"final_answer":"answer"}.
Only request allowlisted AgentOS tools. Never request shell, file, or network tools.
""".strip()


class AgentPlanner:
    def __init__(self, root: Path, model_profile_name: str = "local-stub") -> None:
        self.root = root
        self.model_profile_name = model_profile_name

    def next_step(
        self,
        *,
        task: str,
        role: str,
        tools: list[str],
        previous_results: list[ToolResult],
        step: int,
    ) -> ToolProtocolMessage:
        if self.model_profile_name == "local-stub":
            return _local_stub_plan(task, tools, previous_results, step)
        prompt = _protocol_prompt(task, role, tools, previous_results)
        response = chat_once(
            self.root,
            message=prompt,
            model_profile_name=self.model_profile_name,
            system_prompt=PROTOCOL_INSTRUCTIONS,
        )
        return parse_tool_protocol(response.text)


def parse_tool_protocol(text: str) -> ToolProtocolMessage:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return ToolProtocolMessage(tool_calls=[], final_answer=text.strip() or None)
    try:
        payload = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return ToolProtocolMessage(tool_calls=[], final_answer=text.strip() or None)
    return ToolProtocolMessage.model_validate(payload)


def _protocol_prompt(
    task: str,
    role: str,
    tools: list[str],
    previous_results: list[ToolResult],
) -> str:
    return json.dumps(
        {
            "task": task,
            "role": role,
            "available_tools": tools,
            "previous_tool_results": [
                result.model_dump(mode="json") for result in previous_results
            ],
        },
        sort_keys=True,
    )


def _local_stub_plan(
    task: str,
    tools: list[str],
    previous_results: list[ToolResult],
    step: int,
) -> ToolProtocolMessage:
    if previous_results or step > 1:
        return ToolProtocolMessage(
            tool_calls=[],
            final_answer=f"local-stub final answer after {len(previous_results)} tool result(s).",
        )
    lowered = task.lower()
    if "fake" in lowered and "fake_tool" in tools:
        return ToolProtocolMessage(
            tool_calls=[ToolCall(name="fake_tool", arguments={"query": task})]
        )
    if "brain" in lowered and "brain_search" in tools:
        return ToolProtocolMessage(
            tool_calls=[ToolCall(name="brain_search", arguments={"query": task, "limit": 5})]
        )
    if "policy" in lowered and "policies_check" in tools:
        return ToolProtocolMessage(
            tool_calls=[ToolCall(name="policies_check", arguments={"command": task})]
        )
    if "usage" in lowered and "usage_summary" in tools:
        return ToolProtocolMessage(tool_calls=[ToolCall(name="usage_summary", arguments={})])
    if "memory" in lowered and "memory_search" in tools:
        return ToolProtocolMessage(
            tool_calls=[ToolCall(name="memory_search", arguments={"query": task, "limit": 5})]
        )
    return ToolProtocolMessage(tool_calls=[], final_answer="local-stub final answer without tools.")
