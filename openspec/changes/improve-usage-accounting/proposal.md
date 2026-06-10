# Improve Token And Cost Accounting

## Problem

AgentOS currently keeps cumulative model usage in model configuration metadata.
That is useful for status, but it does not provide durable event history or
summaries by day, model, project/profile, session, or agent.

## Goals

- Add a local SQLite usage database under `.agentos/usage/usage.db`.
- Store usage events without prompt bodies, API keys, or secrets.
- Maintain daily, model, and agent summaries.
- Expose `agentos usage ...` commands.
- Surface session and daily cost in the dashboard bottom bar.
- Surface per-agent token and cost totals in the agent pane.

## Non-Goals

- No prompt logging.
- No provider billing reconciliation.
- No external services.
