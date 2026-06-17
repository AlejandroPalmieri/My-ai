from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from agentos.tools.schemas import ToolDefinition

ToolHandler = Callable[[Path, dict[str, Any]], dict[str, Any]]


class ToolRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, ToolHandler] = {}

    def register(self, definition: ToolDefinition, handler: ToolHandler) -> None:
        if definition.name in self._definitions:
            raise ValueError(f"Tool already registered: {definition.name}")
        self._definitions[definition.name] = definition
        self._handlers[definition.name] = handler

    def list_tools(self) -> list[ToolDefinition]:
        return [self._definitions[name] for name in sorted(self._definitions)]

    def get(self, name: str) -> ToolDefinition:
        try:
            return self._definitions[name]
        except KeyError as error:
            raise KeyError(f"Unknown tool: {name}") from error

    def handler(self, name: str) -> ToolHandler:
        self.get(name)
        return self._handlers[name]

    def names(self) -> set[str]:
        return set(self._definitions)
