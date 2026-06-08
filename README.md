# AgentOS Personal

AgentOS Personal is a local-first foundation for a modular personal AI agent operating system. This MVP creates the repository structure, CLI, SQLite technical memory, SDD/OpenSpec artifact generation, skill registry scanning, policy checks, tests, and developer documentation.

No LLM provider calls, autonomous command execution, external MCP integrations, vector search, or self-modifying prompts are implemented in this first pass.

## Windows PowerShell Setup

```powershell
python --version
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

After activation, validate the CLI and tests:

```powershell
agentos version
pytest
```

If `python`, `agentos`, or `pytest` are not found, confirm the virtual environment is activated. See `docs/windows-powershell.md` for the full Windows workflow and fallback commands that use `.venv\Scripts` directly.

## Commands

```powershell
agentos init
agentos memory add --project demo --title "Decision" --kind decision --content "Use SQLite for local memory." --tag sqlite --source architecture --confidence 0.9
agentos memory search SQLite --project demo
agentos memory list
agentos memory get <memory-id>
agentos memory delete <memory-id>
agentos memory export --format json --output memories.json
agentos memory import memories.json
agentos sdd new add-memory-search
agentos skills scan
agentos policies check --path .env
agentos policies check --command "rm -rf project"
```

`agentos init` also creates `.agentos/profile.yaml` with local project profiles for `godot`, `bioinformatics`, `usmle`, `neocircuit`, and `data-science`.

Operational traces are written locally as JSONL under `.agentos/traces/YYYY-MM-DD.jsonl`.

Memory commands print Rich tables by default. Use `--json` with `memory add`, `memory search`, `memory list`, `memory get`, and `memory delete` when structured output is needed.

## Tests

```powershell
pytest
ruff check .
```
