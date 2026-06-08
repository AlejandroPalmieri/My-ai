# Design: add-strategic-brain-index

## Architecture

`src/agentos/brain/store.py` owns the local SQLite index. It is separate from
`src/agentos/memory/store.py` so strategic documents do not mix with technical
memory rows.

`LocalStrategicBrainService` wraps the store and is resolved through the
existing service container. The CLI calls that service through `agentos brain`.

## Interfaces

CLI:

- `agentos brain ingest <path>`
- `agentos brain search <query>`
- `agentos brain list`
- `agentos brain show <document-id>`

Store path:

- `.agentos/brain/index.db`

Tables:

- `documents`
- `chunks`
- `links`

## Safety

Only explicit user-provided `.md` and `.txt` paths are ingested. The store runs
local policy checks before reading a file. No shell commands, embeddings, LLM
synthesis, or PDF parsing are implemented.
