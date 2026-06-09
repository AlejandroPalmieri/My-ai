# Changelog

## 0.1.0 - 2026-06-08

First local MVP release of AgentOS Personal.

### Added

- Typer CLI with `agentos`, `version`, `doctor`, and `init`.
- Windows PowerShell setup flow and repository-local `agentos.cmd` shim installer.
- SQLite technical memory with FTS5 search when available and `LIKE` fallback.
- Memory add, search, list, get, delete, import, and export commands.
- SDD/OpenSpec artifact workflow with change creation, status, list, phase
  advancement, and archive metadata.
- Local skill registry scanner and validation for `skills/**/SKILL.md` and
  `.agents/skills/**/SKILL.md`.
- Local policy checker for sensitive paths, destructive commands, and approval
  warnings.
- JSONL trace logging with redaction and trace list, show, tail, and export
  commands.
- Project profiles for default, Godot, bioinformatics, USMLE, Neocircuit, and
  data science workflows.
- Rich startup banner, dashboard, and optional interactive dashboard controls.
- Local backup, inspect, restore-with-confirmation, list, and prune commands.
- Experimental local STDIO MCP adapter.
- Strategic Brain v0 local Markdown/text document index.
- Controlled refiner v0 that analyzes traces and writes markdown proposals.
- Local eval runner for memory, policy, skill, and SDD checks.
- Pytest test suite and ruff configuration.

### Security

- Local-first by default.
- No LLM provider calls.
- No autonomous shell execution.
- No automatic secret reading.
- Sensitive trace payloads are redacted.
- Backup creation excludes sensitive paths by policy before files are read.

### Known Limitations

- No external model/provider integrations.
- No autonomous tool orchestration.
- No Textual-based full TUI.
- No vector embeddings or PDF ingestion for Strategic Brain.
- Refiner proposals are not auto-applied.
- MCP server is experimental and STDIO-only.
