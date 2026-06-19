# Explicit Retrieval

AgentOS chat can use local technical memory and Strategic Brain context only when the user explicitly opts in for that request or interactive session. Default chat sends only the user message and optional system prompt.

This is a release checkpoint security requirement: retrieval is off by default in
v0.3.0 and must stay opt-in for both one-shot and interactive chat.

## Quick Path

```powershell
agentos chat once "message" --with-memory
agentos chat once "message" --with-brain
agentos chat once "message" --with-memory --memory-query "architecture decision"
agentos chat once "message" --with-brain --brain-query "planning layer"
agentos chat once "message" --with-memory --with-brain --show-context
agentos chat once "message" --with-memory --dry-run-context
```

## Interactive Session

```powershell
agentos
/memory on
/brain on
/context status
/retrieve memory architecture decision
/retrieve brain planning layer
/context show
/context clear
/memory off
/brain off
```

Interactive opt-in is session-only. It is not persisted globally.

## Context Shape

Retrieved context is prepended as a clearly marked block:

```text
LOCAL OPT-IN CONTEXT
Warning: The following local context was explicitly opted in for this request.
Settings: memory=on limit=5; brain=off limit=5
Technical memory:
- [memory:<id>] Title (kind, project=default): excerpt
END LOCAL OPT-IN CONTEXT
```

## Safety Rules

- Retrieval is off by default.
- Memory and Brain context are never sent unless explicitly opted in.
- Results are limited to excerpts, not whole databases or documents.
- Hidden paths and sensitive-looking content are filtered from retrieval context.
- Traces store counts and ids only, not full retrieved content.
- Traces, backups, files, and arbitrary local data are not retrieved.

## Known Limits

- Strategic Brain retrieval is local text search only; embeddings, graph
  reasoning, PDF ingestion, and synthesis are still future work.
- Context is inserted as bounded excerpts with labels, not as raw database dumps.
