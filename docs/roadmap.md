# Roadmap

## Implemented in MVP

- Python package scaffold under `src/agentos/`.
- Typer CLI with interactive default mode plus version, doctor, init, memory, SDD, skills, and policies commands.
- SQLite technical memory with FTS5 fallback behavior.
- SDD/OpenSpec artifact generator.
- Skill registry scanner for `skills/**/SKILL.md`.
- Policy checker with severity, matched rules, sensitive path detection, dangerous command detection, PowerShell recognition, approval warnings, and default policy files.
- Pytest coverage for core modules and CLI smoke behavior.

## Implemented in Phase 2

- MCP-ready service interfaces, local service adapters, and lazy service container.
- Experimental local STDIO MCP server exposing memory, SDD, skills, and policy tools.
- Strategic Brain v0 local document index for Markdown and text files.
- Local JSONL trace logging under `.agentos/traces/`.
- Trace inspection commands for listing, showing, tailing, and exporting local JSONL events.
- Memory JSON export/import commands.
- Project profile file at `.agentos/profile.yaml`.
- Built-in profiles for default, Godot, bioinformatics, USMLE, Neocircuit, and data science.
- Profile CLI for init, list, show, set, and validate.
- Rich-based neutral startup banner and read-only Zellij-inspired terminal dashboard.
- UI commands for preview, theme listing, theme selection, and banner visibility.
- Windows `agentos.cmd` installer shim and read-only environment diagnostics.

## Intentionally Stubbed

- LLM provider integrations.
- Autonomous command execution.
- Networked or externally hosted MCP server integration.
- GBrain-style graph/vector retrieval.
- Strategic Brain embeddings, PDF ingestion, and LLM synthesis.
- Continual Harness trajectory analysis.
- Self-modifying prompt workflows.
- Strategic brain synthesis and refiner analysis remain service-boundary stubs.
- Interactive terminal pane switching.

## Next Recommended Milestones

1. Replace or extend the experimental MCP JSON-RPC adapter with a formal SDK-backed MCP server if the dependency is adopted.
2. Expand policy checks with structured match types and approvals.
3. Add richer memory update/delete commands with explicit approval gates.
4. Add strategic entity models for future GBrain retrieval.
5. Add evaluation fixtures for future Continual Harness work.
