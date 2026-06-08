# Proposal: add-jsonl-trace-logging

## Summary

Add structured local JSONL trace logging for important CLI operations and expose trace inspection commands. This provides local operational evidence for debugging and future evaluation workflows without adding network dependencies or autonomous behavior.

## Scope

- In scope:
  - Structured event schema with `id`, `timestamp`, `event_type`, `command`, `status`, `project`, `payload`, and `error`.
  - Daily JSONL files under `.agentos/traces/YYYY-MM-DD.jsonl`.
  - Redaction before writing trace payloads and errors.
  - Events for commands, memory operations, SDD changes, skill scans, and policy checks.
  - CLI commands: `traces list`, `traces show`, `traces tail`, and `traces export`.
  - Tests for JSONL validity, redaction, trace reading, and CLI smoke behavior.
  - `docs/traces.md`.
- Out of scope:
  - Remote telemetry.
  - LLM provider logging.
  - Secret scanning by reading files.
  - Exact wall-clock timestamp assertions in tests.

## Risks

- Risk: Traces could accidentally capture sensitive values.
  - Mitigation: Redact sensitive-looking strings and keys before serialization.
- Risk: JSONL output could be wrapped or formatted by Rich.
  - Mitigation: Use `typer.echo` for raw JSONL lines in trace show/tail/export.
- Risk: Logging failures could block core CLI work.
  - Mitigation: Keep the logger small and local with simple file append semantics.
