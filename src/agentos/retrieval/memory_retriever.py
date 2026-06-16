from __future__ import annotations

from pathlib import Path

from agentos.memory.store import MemoryStore
from agentos.retrieval.citations import excerpt, is_sensitive_text
from agentos.retrieval.schemas import MemoryContextItem


def retrieve_memory(root: Path, query: str, *, limit: int = 5) -> list[MemoryContextItem]:
    items: list[MemoryContextItem] = []
    for memory in MemoryStore(root).search(query, limit=limit * 2):
        if is_sensitive_text(memory.title, memory.content, memory.source):
            continue
        items.append(
            MemoryContextItem(
                id=memory.id,
                title=memory.title,
                kind=memory.kind,
                project=memory.project,
                excerpt=excerpt(memory.content),
            )
        )
        if len(items) >= limit:
            break
    return items
