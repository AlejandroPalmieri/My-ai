# Local Evals

AgentOS evals are deterministic local checks for provider wiring, context handling,
retrieval, bounded agent runs, safe tool-calling, streaming, and safety policy
behavior. They do not call external APIs and do not execute shell commands.

## Run evals

```powershell
agentos eval run
agentos eval run --category providers
agentos eval run --category context
agentos eval run --category retrieval
agentos eval run --category agents
agentos eval run --category safety
```

Category aliases map to internal categories:

| Alias | Internal category |
|---|---|
| `providers` | `provider_evals` |
| `streaming` | `streaming_evals` |
| `context` | `context_evals` |
| `retrieval` | `retrieval_evals` |
| `agents` | `agent_run_evals` |
| `tools` | `tool_call_evals` |
| `safety` | `safety_evals` |

## Reports

Each run writes both JSON and Markdown reports under:

```text
.agentos/evals/results/
```

Reports include the eval id, selected category, pass/fail/skip counts, duration,
failure details, environment summary, AgentOS version, and per-case results.

```powershell
agentos eval report --latest
agentos eval report <report-id>
```

Eval workspaces are scoped under `.agentos/evals/workspace/` so generated SQLite
files and local fixtures remain isolated and inspectable.

Release validation should run at least:

```powershell
agentos eval run --category safety
agentos eval run --category providers
```

## Built-in coverage

- Provider evals: local-stub non-streaming/streaming, missing API key warnings,
  and provider factory selection.
- Streaming evals: chunk reconstruction, usage tracking after streams, and
  fallback to non-streaming when streaming is unsupported.
- Context evals: context percentage states, oldest-message compaction, and no
  hidden local data sent by default.
- Retrieval evals: retrieval off by default, memory and Strategic Brain opt-in,
  dry-run context without model calls, and configured max-result limits.
- Agent and tool evals: text-only runs, local-stub tool runs, max-step limits,
  unknown tool blocking, and policy blocking before tool execution.
- Safety evals: `.env` path blocking, no API key values printed, no shell tool
  exposed, and destructive command blocking.

## v0.3.0 Coverage Goal

The checkpoint uses deterministic local evals to prove provider wiring, context
defaults, opt-in retrieval, safe tool-calling, bounded agent runs, and safety
policy behavior without external API calls.
