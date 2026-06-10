from __future__ import annotations

from pathlib import Path

from agentos.agents.registry import AgentRuntimeRegistry


def create_runtime_registry(root: Path) -> AgentRuntimeRegistry:
    return AgentRuntimeRegistry(root)
