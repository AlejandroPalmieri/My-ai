# Roadmap

## Implemented in MVP

- Python package scaffold under `src/agentos/`.
- Typer CLI with version, init, memory, SDD, skills, and policies commands.
- SQLite technical memory with FTS5 fallback behavior.
- SDD/OpenSpec artifact generator.
- Skill registry scanner for `skills/**/SKILL.md`.
- Basic policy checker and default policy files.
- Pytest coverage for core modules and CLI smoke behavior.

## Implemented in Phase 2

- MCP-ready service interfaces and local service adapters.
- Local JSONL trace logging under `.agentos/traces/`.
- Memory JSON export/import commands.
- Project profile file at `.agentos/profile.yaml`.
- Built-in profiles for Godot, bioinformatics, USMLE, Neocircuit, and data science.

## Intentionally Stubbed

- LLM provider integrations.
- Autonomous command execution.
- External MCP server integration.
- GBrain-style graph/vector retrieval.
- Continual Harness trajectory analysis.
- Self-modifying prompt workflows.
- Strategic brain synthesis and refiner analysis remain service-boundary stubs.

## Next Recommended Milestones

1. Add a formal MCP adapter layer over the service interfaces.
2. Expand policy checks with structured match types and approvals.
3. Add richer memory update/delete commands with explicit approval gates.
4. Add strategic entity models for future GBrain retrieval.
5. Add evaluation fixtures for future Continual Harness work.
