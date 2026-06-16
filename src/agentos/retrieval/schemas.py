from __future__ import annotations

from pydantic import BaseModel, Field


class RetrievalSettings(BaseModel):
    with_memory: bool = False
    with_brain: bool = False
    memory_query: str | None = None
    brain_query: str | None = None
    memory_limit: int = Field(default=5, ge=0, le=20)
    brain_limit: int = Field(default=5, ge=0, le=20)


class MemoryContextItem(BaseModel):
    id: str
    title: str
    kind: str
    project: str
    excerpt: str


class BrainContextItem(BaseModel):
    document_id: str
    chunk_id: str
    title: str
    path: str
    chunk_index: int
    excerpt: str


class RetrievalContext(BaseModel):
    settings: RetrievalSettings
    memory_items: list[MemoryContextItem] = Field(default_factory=list)
    brain_items: list[BrainContextItem] = Field(default_factory=list)
    block: str = ""

    @property
    def has_context(self) -> bool:
        return bool(self.memory_items or self.brain_items)

    @property
    def ids(self) -> dict[str, list[str]]:
        return {
            "memory_ids": [item.id for item in self.memory_items],
            "brain_document_ids": [item.document_id for item in self.brain_items],
            "brain_chunk_ids": [item.chunk_id for item in self.brain_items],
        }
