# Add Model Effort Routing

## Problem

AgentOS tracks model profiles and chat usage, but effort levels are only loose
strings. Chat, agents, dashboard status, and future SDD phases need consistent
effort semantics and local routing defaults.

## Proposal

Add typed effort profiles and local route rules in `.agentos/model-routing.yaml`.
Use route defaults for chat and agent runtime entries when explicit effort is
not provided.

## Safety

Routing is local metadata only. It does not read API keys, call providers, or
execute autonomous work.
