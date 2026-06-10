# Add Model-Aware Status Bar

## Problem

The AgentOS dashboard and startup UI show local runtime status, but they do not
surface the active model profile, provider, effort, context usage, token totals,
or estimated cost. This makes the new model configuration layer hard to inspect
during normal startup.

## Proposal

Add a dashboard-facing model status summary populated from the local model
configuration service. Render it in the Rich dashboard bottom bar, plain
dashboard output, and startup runtime panel.

## Safety

- Do not read `.env` files.
- Do not log or render API key values.
- Do not perform provider calls.
- Keep fallback behavior local-first when `.agentos/models.yaml` is missing.
