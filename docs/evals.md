# Evals

AgentOS evals are local smoke checks for the MVP foundation. They do not call
external services and do not execute shell commands.

Run:

```powershell
agentos eval run
```

The first eval set covers:

- `memory_search`: adds a temporary technical memory and verifies local search.
- `policy_check`: verifies `.env` is blocked and `pytest` is allowed.
- `skill_validation`: validates a minimal local `SKILL.md`.
- `sdd_workflow`: creates and advances a temporary SDD change.

Results are written as JSON under:

```text
.agentos/evals/results/
```

Eval workspaces are written under `.agentos/evals/workspace/` so SQLite files
remain stable on Windows while the run is inspectable. The result JSON includes
`id`, `timestamp`, `passed`, `summary`, and per-case `name`, `status`, `detail`,
and `duration_ms` fields. Tests should assert field shape and pass/fail counts,
not exact wall-clock seconds.

The top-level `evals/cases.json` file documents the built-in case set. Future
phases can expand this into richer fixtures, but v0 intentionally stays simple
and deterministic.
