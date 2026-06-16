from __future__ import annotations

from pathlib import Path

from agentos.retrieval.brain_retriever import retrieve_brain
from agentos.retrieval.citations import brain_label, memory_label
from agentos.retrieval.memory_retriever import retrieve_memory
from agentos.retrieval.schemas import RetrievalContext, RetrievalSettings


def build_retrieval_context(
    root: Path,
    message: str,
    settings: RetrievalSettings,
) -> RetrievalContext:
    memory_query = settings.memory_query or message
    brain_query = settings.brain_query or message
    memory_items = (
        retrieve_memory(root, memory_query, limit=settings.memory_limit)
        if settings.with_memory
        else []
    )
    brain_items = (
        retrieve_brain(root, brain_query, limit=settings.brain_limit)
        if settings.with_brain
        else []
    )
    context = RetrievalContext(
        settings=settings,
        memory_items=memory_items,
        brain_items=brain_items,
    )
    context.block = render_context_block(context)
    return context


def render_context_block(context: RetrievalContext) -> str:
    lines = [
        "LOCAL OPT-IN CONTEXT",
        "Warning: The following local context was explicitly opted in for this request.",
        (
            "Settings: "
            f"memory={'on' if context.settings.with_memory else 'off'} "
            f"limit={context.settings.memory_limit}; "
            f"brain={'on' if context.settings.with_brain else 'off'} "
            f"limit={context.settings.brain_limit}"
        ),
    ]
    if context.memory_items:
        lines.append("Technical memory:")
        for item in context.memory_items:
            lines.append(
                f"- [{memory_label(item.id)}] {item.title} "
                f"({item.kind}, project={item.project}): {item.excerpt}"
            )
    if context.brain_items:
        lines.append("Strategic Brain:")
        for item in context.brain_items:
            lines.append(
                f"- [{brain_label(item.document_id, item.chunk_id)}] {item.title} "
                f"({item.path}, chunk={item.chunk_index}): {item.excerpt}"
            )
    if not context.memory_items and not context.brain_items:
        lines.append("No matching local context was retrieved.")
    lines.append("END LOCAL OPT-IN CONTEXT")
    return "\n".join(lines)


def apply_context_to_message(message: str, context: RetrievalContext | None) -> str:
    if context is None or not context.block:
        return message
    return f"{context.block}\n\nUser message:\n{message}"
