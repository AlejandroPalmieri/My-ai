# Add Agent Runtime Registry

## Problem

AgentOS has model metadata and dashboard runtime status, but it does not track
which agents or subagents are currently running or recently active. The UI needs
a local representation before any autonomous runtime exists.

## Proposal

Add a local runtime registry stored at `.agentos/agents/runtime-state.json`.
Expose simple CLI commands for start, list/status, stop, and clear. Show active
agents and subagents in the dashboard right pane.

## Non-Goals

- No autonomous shell execution.
- No automatic LLM call on `agents start`.
- No background process manager.
- No distributed runtime.

## Safety

The registry stores metadata only. It must not read secrets, execute commands,
or send prompts to model providers.
