# Architecture

AgentOS Personal uses small Python modules under `src/agentos/` with explicit boundaries:

- `cli`: Typer commands, terminal output, and the safe local interactive entrypoint.
- `config`: project initialization helpers.
- `memory`: SQLite-backed technical memory with text IDs, schema versioning, FTS5 search when available, and LIKE fallback.
- `sdd`: SDD/OpenSpec workflow generation, metadata, phase advancement, and archive state.
- `skills`: local `skills/**/SKILL.md` scanner and registry writer.
- `policies`: simple local policy files and checker for sensitive paths and destructive commands.
- `diagnostics`: read-only local health checks for CLI setup, SQLite/FTS5, policies, and Windows command discovery.
- `logging`: placeholder package for future structured logging.
- `utils`: placeholder package for shared helpers.
- `services`: MCP-ready service interfaces and local adapters.

The MVP is local-first and does not read secrets automatically. Policy checking is advisory and intentionally separate from any command execution because autonomous execution is out of scope.

## Phase 2 Boundaries

Phase 2 adds service interfaces for `TechnicalMemoryService`, `StrategicBrainService`, `SkillRegistryService`, `PolicyService`, `SDDService`, and `RefinerService`. The local adapters call the existing SQLite memory, skill scanner, policy checker, and SDD generator. Strategic brain and refiner behavior remain explicit stubs so future GBrain and Continual Harness work can attach behind stable interfaces.

The CLI writes local JSONL traces to `.agentos/traces/YYYY-MM-DD.jsonl` for command starts/completions, memory additions, searches, policy violations, and SDD change creation. These traces are local operational evidence, not autonomous self-improvement.

Memory import/export uses JSON so local memories can move between workspaces without introducing a network dependency. Memories are stored under `.agentos/memory.db` in the `memories` table with `id`, `project`, `title`, `kind`, `content`, `tags`, `source`, `confidence`, `created_at`, and `updated_at`. The `schema_version` table records the local memory schema version and initialization is idempotent.

Project profiles live at `.agentos/profile.yaml` and provide local presets for Godot, bioinformatics, USMLE, Neocircuit, and data science contexts.

## SDD/OpenSpec Workflow

Non-trivial changes are tracked under `openspec/changes/<change-name>/`. Change names are validated as lowercase slugs. Each change owns proposal, design, task, apply, verify, sync, and metadata artifacts. `metadata.json` stores the active phase, archive flag, timestamps, and phase history.

Valid phases are `init`, `explore`, `proposal`, `spec`, `design`, `tasks`, `apply`, `verify`, `sync`, and `archive`. The workflow advances one phase at a time by default; `--force` is required for non-linear jumps. Archive marks the change as archived in metadata rather than deleting files.

## Decisions

- SQLite is the only storage dependency for technical memory in the MVP.
- FTS5 is used opportunistically; systems without FTS5 fall back to `LIKE` queries across project, title, kind, content, and tags.
- YAML files are parsed with a tiny list-only parser to avoid adding another dependency in the first pass.
- CLI commands call small service interfaces so future MCP, Hermes-style runtime, Engram memory, GBrain retrieval, and Continual Harness evaluation integrations can reuse the same boundaries.
- SDD archive is metadata-only to preserve local audit history and avoid destructive file movement.
- Windows command discovery uses `scripts/install-agentos-command.ps1` to write a small `agentos.cmd` shim in the user `WindowsApps` directory. The shim delegates to the repository-local `.venv\Scripts\agentos.exe`. The package remains installed in editable mode, so source changes update the CLI behavior without a global install.
- `agentos doctor` is read-only diagnostic behavior. It reports warnings for optional or recoverable setup gaps such as missing FTS5, policy files, or Windows shim configuration, and exits non-zero only for failed critical checks.
- The console-script entrypoint is `agentos.cli.app:main` rather than the raw Typer app. This wrapper detects invocations with no known subcommand and forwards root-level options to the interactive CLI before Typer command parsing runs.
