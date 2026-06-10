# Usage Accounting

AgentOS tracks local token and estimated cost usage in SQLite:

```text
.agentos/usage/usage.db
```

This database stores usage metadata only. It does not store prompt bodies,
system prompts, assistant responses, API keys, environment variable values, or
secret file contents.

## Tables

- `usage_events`
- `usage_daily_summary`
- `usage_model_summary`
- `usage_agent_summary`

Each event records:

- `id`
- `timestamp`
- `session_id`
- `project`
- `profile`
- `provider`
- `model`
- `effort`
- `agent_id`
- `command`
- `input_tokens`
- `output_tokens`
- `total_tokens`
- `estimated_cost_usd`
- `context_used_percent`

If pricing is unknown, AgentOS stores token counts and sets cost to `null`.

## Commands

```powershell
agentos usage summary
agentos usage today
agentos usage by-model
agentos usage by-agent
agentos usage export --format json
agentos usage reset --confirm
```

`agentos models usage` still works and also reports the total token count from
the usage database.

## Chat Integration

`agentos chat once` writes a usage event for successful responses. Existing
trace events include the `usage_event_id`, not prompt content.

Interactive chat uses a session id for the current process so session totals can
be separated from daily totals.

## Dashboard

The bottom status bar shows:

- current session estimated cost;
- total daily estimated cost;
- existing model, effort, context, token, and cumulative cost information.

The right-side `Agents / Subagents` pane reads `usage_agent_summary` and shows
per-agent token and cost totals when usage events include an `agent_id`.

## Safety

- Usage DB is local-only.
- Prompts and responses are not stored by default.
- API keys are never written to usage events or summaries.
- `usage reset` requires `--confirm`.
