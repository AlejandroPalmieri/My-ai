# Add Model Provider Configuration

## Summary

Add a local-first model/provider configuration layer for AgentOS. This change
introduces metadata for providers, model profiles, active model state, estimated
pricing, and usage tracking without adding autonomous agent execution or real
network model calls.

## Goals

- Create `.agentos/models.yaml` with default provider/model profile entries.
- Add local schemas and helpers under `src/agentos/models/`.
- Add CLI commands under `agentos models`.
- Keep API keys out of config; store only environment variable names.
- Treat missing provider API keys as warnings, not hard failures.
- Keep `local-stub` usable without network or secrets.

## Non-Goals

- No prompt execution against real providers.
- No autonomous shell execution.
- No exact pricing claims.
- No `.env` reading.
