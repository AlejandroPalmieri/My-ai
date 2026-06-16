from __future__ import annotations

from pathlib import Path

from agentos.brain.store import StrategicBrainStore
from agentos.retrieval.citations import excerpt, is_hidden_path, is_sensitive_text
from agentos.retrieval.schemas import BrainContextItem


def retrieve_brain(root: Path, query: str, *, limit: int = 5) -> list[BrainContextItem]:
    items: list[BrainContextItem] = []
    for result in StrategicBrainStore(root).search(query, limit=limit * 2):
        if is_hidden_path(result.path) or is_sensitive_text(
            result.path,
            result.title,
            result.chunk,
        ):
            continue
        items.append(
            BrainContextItem(
                document_id=result.document_id,
                chunk_id=result.chunk_id,
                title=result.title,
                path=result.path,
                chunk_index=result.chunk_index,
                excerpt=excerpt(result.chunk),
            )
        )
        if len(items) >= limit:
            break
    return items
