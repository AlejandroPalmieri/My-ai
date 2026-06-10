# Add Context Usage Estimator

## Problem

AgentOS currently shows context usage from model usage counters and estimates
interactive chat context with local inline logic. The UI needs a dedicated,
testable context usage model that can report meaningful `ok`, `warn`,
`critical`, and `unknown` states.

## Goals

- Add a local-first context estimator with conservative token heuristics.
- Represent context usage with a stable `ContextUsage` schema.
- Add a simple session-history compactor that drops oldest messages only when
  needed.
- Integrate context usage into interactive chat and dashboard rendering.
- Document the behavior and known limitations.

## Non-Goals

- No tokenizer dependency.
- No LLM summarization for compaction.
- No automatic file, memory, trace, or brain retrieval.
