# Changelog

## 0.3.0 - 2026-06-18

Release checkpoint for the broader local AgentOS runtime.

### Added

- Streaming chat for one-shot and interactive local chat flows.
- Provider-specific adapters for local-stub, OpenAI, OpenAI-compatible, OpenRouter, Anthropic, and Ollama behind a shared model client boundary.
- Explicit opt-in retrieval from technical memory and Strategic Brain with dry-run and context inspection support.
- Bounded agent runs with provider-neutral tool-call messages and safe allowlisted internal tools.
- Stronger deterministic eval coverage for providers, streaming, context, retrieval, agent runs, tool safety, and safety policies.
- MCP release checkpoint documentation, including the decision to defer formal Python MCP SDK adoption.

### Security

- Retrieval remains off by default and is never added to prompts unless explicitly requested.
- Tool-calling exposes no unrestricted shell, arbitrary file read/write, or network browsing tool.
- `.agentos/`, `.env`, runtime databases, traces, backups, logs, and exports remain ignored.
- Provider configuration stores API key environment variable names only, not key values.

### Known Limitations

- MCP remains a custom local JSON-RPC STDIO implementation while SDK adoption is deferred.
- Strategic Brain still has no embeddings, graph reasoning, PDF ingestion, or LLM synthesis.
- Provider adapters are intentionally minimal and do not use vendor SDKs.
- Agent runs are bounded local tool loops, not autonomous background workers.

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
