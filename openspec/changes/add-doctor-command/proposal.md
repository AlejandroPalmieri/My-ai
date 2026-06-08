# Proposal: add-doctor-command

## Summary

Add a read-only `agentos doctor` command that diagnoses local setup problems without requiring virtual environment activation. This matters because the project now supports a persistent Windows `agentos.cmd` shim, and users need a quick way to confirm Python, the local CLI executable, SQLite/FTS5, policy files, and PATH/shim wiring.

## Scope

- In scope:
  - Add a small diagnostics module with typed check results.
  - Add a local doctor service boundary.
  - Add `agentos doctor` with Rich table output and non-zero exit on critical failures.
  - Document the command in README, Windows workflow, architecture, roadmap, and implementation status.
  - Add unit and CLI smoke tests.
- Out of scope:
  - Automatic repair of missing setup pieces.
  - Reading secrets, environment files, credentials, or user data.
  - Network checks, provider checks, MCP server checks, or LLM integration checks.

## Risks

- Risk: A diagnostic command could become too broad and accidentally inspect sensitive files.
  - Mitigation: Keep checks read-only and limited to known project setup paths, SQLite in-memory probes, and the Windows shim file.
- Risk: Optional capabilities such as FTS5 may be unavailable on some systems.
  - Mitigation: Report optional setup gaps as warnings, not failures.
