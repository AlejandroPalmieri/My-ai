# Strategic Brain V0

AgentOS Strategic Brain v0 is a local document index for strategic knowledge.
It is not a full GBrain clone.

## Storage

Files are indexed into:

```text
.agentos/brain/
.agentos/brain/index.db
```

SQLite tables:

- `documents`: path, title, content hash, created and updated timestamps.
- `chunks`: document chunks used for search.
- `links`: reserved for future lightweight document links.

Search uses SQLite FTS5 when available. If FTS5 is unavailable, AgentOS falls
back to `LIKE` search over document title, path, and chunk content.

## Commands

```powershell
agentos brain ingest .\notes\strategy.md
agentos brain search "planning layer"
agentos brain list
agentos brain show <document-id>
```

Supported input files:

- `.md`
- `.txt`

Re-ingesting the same resolved file path updates the existing document and
replaces its chunks instead of creating duplicates.

## Boundaries

Strategic Brain is separate from technical memory:

- Technical memory stores short operational notes and decisions.
- Strategic Brain indexes local documents and longer strategic references.

## Current Limitations

- No embeddings.
- No LLM synthesis.
- No PDF ingestion.
- No graph reasoning.
- No automatic directory crawling.
- Only user-specified `.md` and `.txt` files are read.

Policy checks run before reading a file, so sensitive paths remain blocked.
