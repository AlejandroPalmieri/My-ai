# Architecture

AgentOS Personal uses small Python modules under `src/agentos/` with explicit boundaries:

- `cli`: Typer commands and terminal output.
- `config`: project initialization helpers.
- `memory`: SQLite-backed technical memory with FTS5 search when available and LIKE fallback.
- `sdd`: SDD/OpenSpec artifact generation.
- `skills`: local `skills/**/SKILL.md` scanner and registry writer.
- `policies`: simple local policy files and checker for sensitive paths and destructive commands.
- `logging`: placeholder package for future structured logging.
- `utils`: placeholder package for shared helpers.
- `services`: MCP-ready service interfaces and local adapters.

The MVP is local-first and does not read secrets automatically. Policy checking is advisory and intentionally separate from any command execution because autonomous execution is out of scope.

## Phase 2 Boundaries

Phase 2 adds service interfaces for `TechnicalMemoryService`, `StrategicBrainService`, `SkillRegistryService`, `PolicyService`, `SDDService`, and `RefinerService`. The local adapters call the existing SQLite memory, skill scanner, policy checker, and SDD generator. Strategic brain and refiner behavior remain explicit stubs so future GBrain and Continual Harness work can attach behind stable interfaces.

The CLI writes local JSONL traces to `.agentos/traces/YYYY-MM-DD.jsonl` for command starts/completions, memory additions, searches, policy violations, and SDD change creation. These traces are local operational evidence, not autonomous self-improvement.

Memory import/export uses JSON so local memories can move between workspaces without introducing a network dependency.

Project profiles live at `.agentos/profile.yaml` and provide local presets for Godot, bioinformatics, USMLE, Neocircuit, and data science contexts.

## Decisions

- SQLite is the only storage dependency for technical memory in the MVP.
- FTS5 is used opportunistically; systems without FTS5 fall back to `LIKE` queries.
- YAML files are parsed with a tiny list-only parser to avoid adding another dependency in the first pass.
- CLI commands call small service interfaces so future MCP, Hermes-style runtime, Engram memory, GBrain retrieval, and Continual Harness evaluation integrations can reuse the same boundaries.
