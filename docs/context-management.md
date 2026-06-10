# Context Management

AgentOS estimates context usage locally so chat and the terminal dashboard can
show a useful percentage without adding tokenizer dependencies.

## ContextUsage

`agentos.context.schemas.ContextUsage` records:

- `model_profile`
- `context_window_tokens`
- `estimated_input_tokens`
- `estimated_output_tokens`
- `reserved_output_tokens`
- `total_estimated_tokens`
- `used_percent`
- `status`

The status values are:

- `ok`: below 80 percent.
- `warn`: 80 percent or higher.
- `critical`: 95 percent or higher.
- `unknown`: the model profile has no known context window.

When the context window is unknown, dashboard output renders `ctx: n/a`.

## Token Estimation

Provider-reported token usage is used when available. When a provider does not
return usage, AgentOS uses a conservative character-based estimate of roughly
three characters per token. This is intentionally simple and local-first.

AgentOS does not add a tokenizer dependency yet. Exact token counts can differ
by provider and model.

## Interactive Chat

The interactive chat loop estimates context from:

- the system prompt;
- session-only conversation history;
- the latest user message;
- the latest assistant response after a turn completes.

It does not automatically include memory entries, strategic brain documents,
trace logs, files, or secrets. Retrieval-augmented chat remains a future
feature.

At 80 percent or higher, AgentOS prints a visible warning. At 95 percent or
higher, it drops the oldest session messages until the session is under the
critical threshold when possible. The compactor does not summarize with an LLM.

## Dashboard

The dashboard bottom bar uses `ContextUsage` from the active model state:

```text
model: local-stub|provider: local|effort: medium|ctx: 12.00%|tok: 1.2k/10.0k|i/o/t: 800/400/1200|cost: $0.000000
```

Warn and critical context states use warning and danger styling in Rich-capable
terminals. Plain output keeps the same values as text.

## Limitations

- Token estimation is approximate unless the provider reports usage.
- Compaction drops oldest session messages; it does not summarize them.
- Context tracking is session and usage focused; no external documents are
  included automatically.
- Context windows come from `.agentos/models.yaml` and may need user updates for
  real providers.
