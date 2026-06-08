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

To make `agentos` available in new terminals without activating `.venv` every time, run this once from the repository root:

```powershell
.\scripts\install-agentos-command.ps1
```

Open a new PowerShell terminal and run:

```powershell
agentos version
```

The installer writes a small `agentos.cmd` shim to your user `WindowsApps` directory that calls this repository's `.venv\Scripts\agentos.exe`. Because the project is installed in editable mode, normal source changes are reflected automatically. Re-run the installer after dependency, virtual environment, or CLI entrypoint changes.

## Commands

```powershell
agentos
agentos --no-banner
agentos --no-dashboard
agentos --plain
agentos --theme zellij-neutral
agentos --model local --profile godot
agentos version
agentos doctor
agentos init
agentos mcp serve
agentos dashboard --theme zellij-neutral
agentos ui preview
agentos ui themes
agentos ui set-theme zellij-neutral
agentos ui banner --show
agentos ui banner --hide
agentos profile init
agentos profile list
agentos profile show
agentos profile set usmle
agentos profile validate
agentos memory add --project demo --title "Decision" --kind decision --content "Use SQLite for local memory." --tag sqlite --source architecture --confidence 0.9
agentos memory search SQLite --project demo
agentos memory list
agentos memory get <memory-id>
agentos memory delete <memory-id>
agentos memory export --format json --output memories.json
agentos memory import memories.json
agentos brain ingest .\docs\strategy.md
agentos brain search "planning layer"
agentos brain list
agentos brain show <document-id>
agentos sdd new add-memory-search
agentos skills scan
agentos skills list
agentos skills show sqlite-memory
agentos skills validate
agentos policies check --path .env
agentos policies check --command "rm -rf project"
agentos policies list
agentos policies explain
agentos traces list
agentos traces show --date 2026-06-08
agentos traces tail
agentos traces export
```

`agentos init` also creates `.agentos/profile.yaml` with local project profiles for `default`, `godot`, `bioinformatics`, `usmle`, `neocircuit`, and `data-science`.

Profiles control local work-mode defaults. For example:

```powershell
agentos profile set usmle
agentos memory add --title "Weak area" --content "Review renal physiology."
```

When `--project` is omitted, `memory add` uses the active profile's `memory_project`. See `docs/profiles.md`.

The experimental MCP server exposes selected local capabilities over STDIO:

```powershell
agentos mcp serve
```

It is local-only by default, does not execute shell commands, and does not expose delete operations. See `docs/mcp.md` for the Codex MCP config and security notes.

Operational traces are written locally as JSONL under `.agentos/traces/YYYY-MM-DD.jsonl`.

Trace commands inspect local JSONL events: `agentos traces list`, `agentos traces show --date YYYY-MM-DD`, `agentos traces tail`, and `agentos traces export`. Trace payloads redact sensitive values before writing. See `docs/traces.md`.

Running `agentos` without a subcommand shows the neutral AGENTOS startup intro and a read-only Zellij-inspired terminal dashboard, then starts the local interactive CLI. Unknown root-level options are forwarded to the interactive session so future model/profile/runtime flags can be handled there without breaking command parsing.

UI settings live in `.agentos/config.yaml`:

```yaml
ui:
  show_banner: true
  open_dashboard_on_start: true
  theme: zellij-neutral
  compact_mode: auto
```

Use `agentos --no-dashboard` to skip the dashboard for a faster startup, `agentos --plain` for plain text output, and `agentos ui themes` to list available themes. See `docs/ui.md`.

`agentos doctor` checks the local Python version, project root, repository-local CLI executable, SQLite, SQLite FTS5 availability, policy files, and the Windows `agentos.cmd` shim when running on Windows. Missing FTS5, policies, or shim configuration are reported as warnings; missing critical runtime pieces return a non-zero exit code.

Policy checks return `allow`, `warn`, or `block` with a reason and matched rule. See `docs/security.md` for examples and policy file details.

Memory commands print Rich tables by default. Use `--json` with `memory add`, `memory search`, `memory list`, `memory get`, and `memory delete` when structured output is needed.

Strategic Brain v0 indexes local `.md` and `.txt` documents under `.agentos/brain/index.db`. It uses SQLite FTS5 when available, falls back to `LIKE`, and stays separate from technical memory. No embeddings, LLM synthesis, or PDF ingestion are implemented yet. See `docs/strategic-brain.md`.

Skills can live in project-local `skills/**/SKILL.md` or Codex-style `.agents/skills/**/SKILL.md`. Run `agentos skills scan` to write `.agentos/skill-registry.json`, `agentos skills list` to inspect entries, and `agentos skills show <skill-name>` to load full skill content on demand.

## Tests

```powershell
pytest
ruff check .
```
