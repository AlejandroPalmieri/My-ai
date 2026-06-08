# Proposal: add-strategic-brain-index

## Summary

Implement StrategicBrainService v0 as a local SQLite document index for
Markdown and text files. This creates a simple strategic knowledge layer without
trying to clone full GBrain behavior.

## Scope

- In scope:
  - `.agentos/brain/index.db`.
  - `documents`, `chunks`, and reserved `links` tables.
  - Markdown/text ingestion with chunking and content hashes.
  - Re-ingest update behavior by resolved path.
  - FTS5 search with LIKE fallback.
  - `agentos brain ingest/search/list/show`.
  - StrategicBrainService local adapter methods.
- Out of scope:
  - Embeddings.
  - LLM synthesis.
  - PDF ingestion.
  - Full GBrain graph reasoning.
  - Automatic directory crawling.

## Risks

- Risk: accidentally reading sensitive files. Mitigation: policy checks run
  before document content is read.
- Risk: conflating strategic documents with technical memory. Mitigation:
  storage and CLI live under separate `brain` module/commands.
