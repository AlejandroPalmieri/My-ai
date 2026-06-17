# Architecture

AgentOS Personal uses small Python modules under `src/agentos/` with explicit boundaries:

- `cli`: Typer commands, terminal output, and the safe local interactive entrypoint.
- `config`: project initialization helpers and profile models.
- `memory`: SQLite-backed technical memory with text IDs, schema versioning, FTS5 search when available, and LIKE fallback.
- `brain`: SQLite-backed local strategic document index for Markdown and text documents.
- `backups`: local zip backup, inspect, restore, and prune behavior for AgentOS metadata.
- `sdd`: SDD/OpenSpec workflow generation, metadata, phase advancement, and archive state.
- `skills`: local `skills/**/SKILL.md` scanner and registry writer.
- `policies`: local policy files and checker for sensitive paths, destructive commands, approval warnings, severity, reasons, and matched rules.
- `diagnostics`: read-only local health checks for CLI setup, SQLite/FTS5, policies, and Windows command discovery.
- `evals`: deterministic local eval runner for MVP memory, policy, skill, and SDD checks.
- `logging`: local JSONL trace logging, redaction, and trace readers.
- `mcp`: experimental local STDIO MCP adapter and JSON-RPC server.
- `refiner`: controlled trace analysis and proposal generation without auto-edit behavior.
- `ui`: Rich-based terminal theme, banner, pane layout, and read-only dashboard rendering.
- `utils`: placeholder package for shared helpers.
- `services`: MCP-ready service interfaces and local adapters.

The MVP is local-first and does not read secrets automatically. Policy checking is intentionally separate from any command execution because autonomous execution is out of scope.

## Service Boundaries

The CLI resolves local dependencies through a lazy `ServiceContainer`:

```text
agentos CLI
  -> ServiceContainer(root)
      -> TechnicalMemoryService -> SQLite memory store
      -> SDDService             -> OpenSpec/SDD generator
      -> SkillRegistryService   -> local SKILL.md scanner
      -> PolicyService          -> local policy checker
      -> TraceService           -> local JSONL trace logger
      -> ProfileService         -> .agentos/profile.yaml
      -> StrategicBrainService  -> local document index plus TODO synthesis stub
      -> RefinerService         -> local trace analysis and proposal writer
      -> BackupService          -> local zip backups and confirmed restore
```

Service protocols live in `src/agentos/services/interfaces.py`; local-first
adapters live in `src/agentos/services/local.py`; the container lives in
`src/agentos/services/container.py`. This keeps CLI handlers stable while future
MCP, Engram, GBrain, Hermes, and Continual Harness integrations attach behind
the same interfaces.

Strategic brain v0 indexes local Markdown and text documents into
`.agentos/brain/index.db`. It remains separate from technical memory and does
not implement embeddings, PDF ingestion, graph reasoning, or LLM synthesis.
Strategic synthesis remains an explicit TODO stub.

## Phase 2 Boundaries

The CLI writes local JSONL traces to `.agentos/traces/YYYY-MM-DD.jsonl` for command starts/completions/failures, memory additions/searches/deletes, policy checks/violations, skill scans, and SDD changes. These traces are local operational evidence, not autonomous self-improvement.

Local eval results are written under `.agentos/evals/results/`. The first eval
runner exercises memory search, policy checks, skill validation, and SDD
workflow in isolated local workspaces.

The controlled refiner reads recent local traces and detects repeated command
failures, frequent policy violations, and memory searches that returned zero
results. It writes markdown proposals under `.agentos/refiner/proposals/`.
The refiner does not edit `AGENTS.md`, skills, policies, or source code, and
human approval is required before any future implementation.

Local backups are written as zip files under `.agentos/backups/`. Backup
creation checks each candidate path against local policy rules before reading or
adding it to the archive. Sensitive paths are excluded and recorded in backup
metadata. Restore requires explicit `--confirm` and only writes files contained
in the selected archive.

Memory import/export uses JSON so local memories can move between workspaces without introducing a network dependency. Memories are stored under `.agentos/memory.db` in the `memories` table with `id`, `project`, `title`, `kind`, `content`, `tags`, `source`, `confidence`, `created_at`, and `updated_at`. The `schema_version` table records the local memory schema version and initialization is idempotent.

Strategic Brain document indexing stores `documents`, `chunks`, and reserved
`links` under `.agentos/brain/index.db`. Search uses FTS5 when available and
falls back to `LIKE`, matching the local-first behavior used by technical
memory.

Project profiles live at `.agentos/profile.yaml` and provide local presets for default, Godot, bioinformatics, USMLE, Neocircuit, and data science contexts. The active profile supplies `memory_project` for `memory add` when `--project` is omitted, and its `blocked_paths` extend local policy checks.

UI settings live at `.agentos/config.yaml`. The built-in `zellij-neutral` theme renders a neutral dark Rich dashboard when `agentos` is run without a subcommand. Dashboard data collection is separate from rendering and only shows compact metadata such as memory titles, SDD phases, trace event names, and local file paths. The dashboard also has an optional Rich-based interactive mode with pane focus, refresh, backup creation, skill scanning, and eval runs. These actions call AgentOS local services directly and do not execute shell commands.

The experimental MCP server runs over local STDIO via `agentos mcp serve`. It
exposes selected service-container capabilities as tools and intentionally does
not expose memory deletion or shell execution. The first version uses a small
MCP-shaped JSON-RPC adapter instead of adding a Python MCP SDK dependency.

## SDD/OpenSpec Workflow

Non-trivial changes are tracked under `openspec/changes/<change-name>/`. Change names are validated as lowercase slugs. Each change owns proposal, design, task, apply, verify, sync, and metadata artifacts. `metadata.json` stores the active phase, archive flag, timestamps, and phase history.

Valid phases are `init`, `explore`, `proposal`, `spec`, `design`, `tasks`, `apply`, `verify`, `sync`, and `archive`. The workflow advances one phase at a time by default; `--force` is required for non-linear jumps. Archive marks the change as archived in metadata rather than deleting files.

## Decisions

- SQLite is the only storage dependency for technical memory in the MVP.
- FTS5 is used opportunistically; systems without FTS5 fall back to `LIKE` queries for memory and strategic brain search.
- YAML files are parsed with a tiny list-only parser to avoid adding another dependency in the first pass.
- CLI commands call the service container instead of concrete local adapters so future MCP, Hermes-style runtime, Engram memory, GBrain retrieval, and Continual Harness evaluation integrations can reuse the same boundaries.
- SDD archive is metadata-only to preserve local audit history and avoid destructive file movement.
- Windows command discovery uses `scripts/install-agentos-command.ps1` to write a small `agentos.cmd` shim in the user `WindowsApps` directory. The shim delegates to the repository-local `.venv\Scripts\agentos.exe`. The package remains installed in editable mode, so source changes update the CLI behavior without a global install.
- `agentos doctor` is read-only diagnostic behavior. It reports warnings for optional or recoverable setup gaps such as missing FTS5, policy files, or Windows shim configuration, and exits non-zero only for failed critical checks.
- The console-script entrypoint is `agentos.cli.app:main` rather than the raw Typer app. This wrapper detects invocations with no known subcommand and forwards root-level options to the interactive CLI before Typer command parsing runs.
- Policy decisions use `allow`, `warn`, and `block`. Sensitive path and destructive command rules block; approval rules warn; safe inputs allow. The checker is local text analysis only and never executes checked commands.
- Trace events use a stable JSONL schema with `id`, `timestamp`, `event_type`, `command`, `status`, `project`, `payload`, and `error`. Sensitive-looking values are redacted before writing.
- Chat streaming is implemented at the model provider boundary with normalized events (`message_start`, `content_delta`, `message_done`, `usage_delta`, `error`). CLI and interactive chat consume deltas without logging prompt or response bodies, then record usage after completion.
- Model providers are selected through a provider factory and expose a shared adapter interface for config validation, chat, streaming chat, usage parsing/estimation, and normalized errors. Provider-specific adapters keep OpenAI, OpenRouter, Anthropic, Ollama, OpenAI-compatible, and local-stub behavior isolated behind the same model client boundary.
- Agent tool-calling uses a provider-neutral JSON protocol and an allowlisted internal tool registry. The executor validates tool names and required arguments, checks local policies, enforces per-run call limits and approval requirements, logs tool traces, and does not expose shell execution, arbitrary file access, or network browsing.
- Profile validation treats unknown preferred skill names as warnings so profile configuration can reference planned skills without failing the whole profile file.
- The startup UI uses Rich, not Textual. It is local-first and avoids external service calls.
- The dashboard interactive mode uses Rich and local service calls instead of Textual. It supports pane focus and safe local actions, but still does not reveal redacted policy values or run arbitrary shell commands.
- The MCP server is STDIO-only and local by default. It exposes policy checking as a tool so MCP-compatible agents can ask AgentOS to evaluate sensitive paths or dangerous command text without executing it.
- The refiner is proposal-only. It analyzes trace evidence but has no production self-modification path.
- Backup archives use zip for Windows compatibility. Restore requires explicit confirmation and prune keeps the newest 10 backups by default.
