# AgentOS Personal

AgentOS Personal is a local-first foundation for a modular personal AI agent operating system. This MVP creates the repository structure, CLI, SQLite technical memory, SDD/OpenSpec artifact generation, skill registry scanning, policy checks, tests, and developer documentation.

No LLM provider calls, autonomous command execution, external MCP integrations, vector search, or self-modifying prompts are implemented in this first pass.

## Setup

```powershell
uv sync --extra dev
```

Run commands through `uv`:

```powershell
uv run agentos version
```

## Commands

```powershell
uv run agentos init
uv run agentos memory add --project demo --title "Decision" --kind decision --content "Use SQLite for local memory." --tag sqlite
uv run agentos memory search SQLite --project demo
uv run agentos memory export --format json --output memories.json
uv run agentos memory import memories.json
uv run agentos sdd new add-memory-search
uv run agentos skills scan
uv run agentos policies check --path .env
uv run agentos policies check --command "rm -rf project"
```

`agentos init` also creates `.agentos/profile.yaml` with local project profiles for `godot`, `bioinformatics`, `usmle`, `neocircuit`, and `data-science`.

Operational traces are written locally as JSONL under `.agentos/traces/YYYY-MM-DD.jsonl`.

## Tests

```powershell
uv run pytest
uv run ruff check .
```
