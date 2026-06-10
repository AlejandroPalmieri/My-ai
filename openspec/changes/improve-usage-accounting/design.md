# Design

## Storage

`agentos.usage.store.UsageStore` owns `.agentos/usage/usage.db`.

Tables:

- `usage_events`
- `usage_daily_summary`
- `usage_model_summary`
- `usage_agent_summary`

Events store metadata and token/cost counts only. They do not store prompt
body, system prompt, response text, API keys, or environment variable values.

## Summaries

Summaries are updated transactionally after each event insert. If any event in
a summary has unknown cost, the summary cost remains `null`.

## Integration

`models.usage.record_usage` continues to update the existing active model usage
metadata, and also inserts a usage event when enough request metadata is
available. `chat_once` supplies provider, model, effort, command, context
percentage, and session id.

Dashboard data reads the usage database for latest-session cost, daily cost,
and agent totals.
