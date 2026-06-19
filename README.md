# AgentOS Personal

## What AgentOS Is

AgentOS Personal is a local-first foundation for a modular personal AI agent operating system. This MVP creates the repository structure, CLI, SQLite technical memory, SDD/OpenSpec artifact generation, skill registry scanning, policy checks, tests, and developer documentation.

The v0.3.0 release checkpoint is the first broader local runtime checkpoint: a safe command-line workspace with streaming chat, provider-specific model adapters, explicit opt-in retrieval, allowlisted agent tool-calling, stronger local evals, and a documented MCP SDK deferral.

External provider calls require explicit configuration through environment variables. AgentOS still does not implement autonomous shell execution, externally hosted MCP integrations, vector search, or self-modifying prompts.

## v0.3.0 Checkpoint

- Streaming chat is available for `chat once` and interactive chat when the active provider supports it.
- Provider adapters cover `local-stub`, OpenAI, OpenAI-compatible, OpenRouter, Anthropic, and Ollama behind one model client boundary.
- Technical memory and Strategic Brain retrieval are explicit opt-in only with `--with-memory`, `--with-brain`, or session-local interactive commands.
- Agent runs can call only allowlisted internal tools; there is no shell, arbitrary file read/write, or network browsing tool.
- Local evals cover providers, streaming, context, retrieval, agent runs, tool safety, and safety policy behavior.
- The official Python MCP SDK is intentionally deferred; see `docs/mcp.md` and `docs/mcp-sdk-decision.md`.

See `docs/v0.3.0-release-notes.md` for the release checkpoint, validation, security posture, known limitations, and v0.4.0 milestones.

## One-Line Go CLI Install

The Go CLI migration starts with a small native `agentos` binary for stable commands while the Python CLI remains the full-featured runtime.

```sh
curl -fsSL https://raw.githubusercontent.com/AlejandroPalmieri/My-ai/main/scripts/install.sh | sh
```

After installation, open a new terminal if `~/.local/bin` was not already on `PATH`, then run:

```sh
agentos version
agentos doctor
```

See `docs/go-cli-migration.md` for the current Go command scope and migration rule.

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

## Quickstart

```powershell
agentos init
agentos doctor
agentos profile show
agentos
agentos memory add --title "First note" --content "AgentOS is running locally."
agentos memory search AgentOS
agentos dashboard --plain
```

For a richer terminal view:

```powershell
agentos dashboard --interactive
```

Before larger local changes:

```powershell
agentos backup create
```

## Core Commands

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
agentos models init
agentos models status
agentos models providers
agentos models provider-status
agentos models test local-stub
agentos chat once "Hello AgentOS"
agentos chat once "Hello AgentOS" --stream
agentos chat once "Hello AgentOS" --no-stream
agentos agents status
agentos usage summary
agentos mcp serve
agentos mcp tools
agentos mcp status
agentos eval run
agentos eval run --category safety
agentos eval report --latest
agentos refiner analyze
agentos refiner propose
agentos refiner list-proposals
agentos backup create
agentos backup list
agentos backup inspect <backup-id>
agentos backup restore <backup-id> --confirm
agentos backup prune
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
agentos models init
agentos models list
agentos models providers
agentos models provider-status
agentos models show
agentos models set local-stub
agentos models test local-stub --stream
agentos models status
agentos models usage
agentos models reset-usage --confirm
agentos models effort list
agentos models effort show high
agentos models route list
agentos models route set default_chat --model local-stub --effort medium
agentos chat once "Explain AgentOS briefly."
agentos chat once "Explain AgentOS briefly." --with-memory --show-context
agentos chat once "Explain AgentOS briefly." --with-brain --dry-run-context
agentos chat once "Explain AgentOS briefly." --json
agentos chat status
agentos agents start --name Planner --role planning --task "Plan next change" --model local-stub
agentos agents run --name Planner --role planning --task "Search memory for architecture" --tools
agentos tools list
agentos tools show memory_search
agentos tools test policies_check --json-input '{"command":"pytest"}'
agentos agents list
agentos agents status
agentos agents stop <agent-id>
agentos agents clear --confirm
agentos usage summary
agentos usage today
agentos usage by-model
agentos usage by-agent
agentos usage export --format json
agentos usage reset --confirm
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

`agentos init` also creates `.agentos/models.yaml` with local model provider
metadata and editable pricing estimates. API key values are not stored; AgentOS
stores environment variable names only. `local-stub` works without network or
API keys. See `docs/models.md` and `docs/providers.md`.

`agentos chat once` sends one explicit user message, plus an optional `--system`
prompt, to the active model profile. It supports `--stream` and `--no-stream`,
and it does not automatically include local files, memories, traces, or secrets.
The default `local-stub` provider works offline. See `docs/chat.md` and
`docs/streaming-chat.md`. Local memory and Strategic Brain retrieval are explicit
opt-in only; see `docs/retrieval.md`.

`agentos agents run --tools` enables bounded tool-calling through allowlisted
internal AgentOS tools only. There is no shell, arbitrary file access, or network
browsing tool in v0. See `docs/tools.md`, `docs/agents.md`, and `docs/runtime.md`.

Usage accounting is stored locally in `.agentos/usage/usage.db`. It records
token and estimated cost metadata by session, day, project/profile, model, and
agent without storing prompt bodies. See `docs/usage.md`.

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

The official Python MCP SDK (`mcp`) is intentionally deferred for now; AgentOS
keeps the current custom JSON-RPC STDIO implementation because the active MCP
needs are local-only and do not justify the extra dependency or async/server
abstraction yet. See `docs/mcp-sdk-decision.md`.

Operational traces are written locally as JSONL under `.agentos/traces/YYYY-MM-DD.jsonl`.

Trace commands inspect local JSONL events: `agentos traces list`, `agentos traces show --date YYYY-MM-DD`, `agentos traces tail`, and `agentos traces export`. Trace payloads redact sensitive values before writing. See `docs/traces.md`.

Running `agentos` without a subcommand shows the neutral AGENTOS startup intro
and a read-only Zellij-inspired terminal dashboard, then starts the interactive
model chat loop. Unknown root-level options are forwarded to the interactive
session so future model/profile/runtime flags can be handled there without
breaking command parsing.

UI settings live in `.agentos/config.yaml`:

```yaml
ui:
  show_banner: true
  open_dashboard_on_start: true
  theme: zellij-neutral
  compact_mode: auto
chat:
  max_history_messages: 20
```

Use `agentos --no-dashboard` to skip the dashboard for a faster startup, `agentos --plain` for plain text output, and `agentos ui themes` to list available themes. See `docs/ui.md`.

Interactive chat commands include `/model list`, `/model set <profile>`,
`/effort low|medium|high|max`, `/stream on`, `/stream off`, `/stream status`,
`/usage`, `/usage reset --confirm`, `/agents`, `/clear`, `/dashboard`, and
`/memory search <query>`. Any other input is sent to the active model. AgentOS
does not automatically include memory, brain documents, traces, or local files
in prompts. Retrieval is session-local opt-in only with `/memory on`,
`/brain on`, and `/retrieve ...`. See `docs/interactive-chat.md` and
`docs/retrieval.md`.

## Dashboard

Run the read-only local dashboard from PowerShell:

```powershell
agentos dashboard
agentos dashboard --plain
agentos dashboard --interactive
agentos dashboard --interactive --plain
```

The dashboard shows the active profile, memory count, recent memories, active
SDD changes, registered skills, recent policy violations, and latest trace
events. The bottom bar and startup panel also show the active model, provider,
effort, context usage, cumulative input/output/total tokens, and estimated
cost from local model metadata, plus current session and daily cost from local
usage accounting. `--plain` uses text-only output, and the command also falls
back to plain output when terminal capabilities are limited.
The right-side pane shows active agents/subagents from the local runtime
registry, with status, role, model profile, effort, current task, token counts,
and estimated cost. See `docs/agents.md`.

Example bottom status:

```text
[q] quit | [tab] pane | [r] refresh | [m] memory
model: local-stub|provider: local|effort: low|ctx: 0.00%|tok: 0/10.0k|i/o/t: 0/0/0|cost: $0.000000
session: $0.000000|today: $0.000000
```

Interactive dashboard controls:

- `tab` or `n`: move pane focus.
- `m`, `s`, `p`, `t`, `o`: focus memory, SDD, policies, traces, or overview.
- `r`: refresh dashboard data.
- `b`: create a local backup.
- `k`: scan skills and update `.agentos/skill-registry.json`.
- `e`: run local evals.
- `u`: explain why sensitive policy values remain redacted.
- `q`: quit.

The interactive dashboard still does not execute shell commands and does not
reveal redacted sensitive values.

`agentos doctor` checks the local Python version, project root, repository-local CLI executable, SQLite, SQLite FTS5 availability, policy files, and the Windows `agentos.cmd` shim when running on Windows. Missing FTS5, policies, or shim configuration are reported as warnings; missing critical runtime pieces return a non-zero exit code.

Policy checks return `allow`, `warn`, or `block` with a reason and matched rule. See `docs/security.md` for examples and policy file details.

Memory commands print Rich tables by default. Use `--json` with `memory add`, `memory search`, `memory list`, `memory get`, and `memory delete` when structured output is needed.

Strategic Brain v0 indexes local `.md` and `.txt` documents under `.agentos/brain/index.db`. It uses SQLite FTS5 when available, falls back to `LIKE`, and stays separate from technical memory. No embeddings, LLM synthesis, or PDF ingestion are implemented yet. See `docs/strategic-brain.md`.

Local evals run deterministic checks for providers, streaming, context, retrieval,
agent runs, safe tool-calling, and safety policies. Results are stored as JSON and
Markdown under `.agentos/evals/results/`; inspect them with
`agentos eval report --latest` or `agentos eval report <report-id>`. See
`docs/evals.md`.

The controlled refiner analyzes recent trace logs and writes human-reviewed improvement proposals under `.agentos/refiner/proposals/`. It does not edit `AGENTS.md`, skills, policies, or source code. See `docs/refiner.md`.

Local backups are zip archives under `.agentos/backups/` for AgentOS configuration and metadata. Restore requires `--confirm`, and sensitive paths are excluded by policy before files are read or added. See `docs/backups.md`.

Skills can live in project-local `skills/**/SKILL.md` or Codex-style `.agents/skills/**/SKILL.md`. Run `agentos skills scan` to write `.agentos/skill-registry.json`, `agentos skills list` to inspect entries, and `agentos skills show <skill-name>` to load full skill content on demand.

## Safety Notes

- AgentOS is local-first and stores runtime data under `.agentos/`.
- Do not commit `.agentos/`, local databases, traces, backups, `.env`, keys, tokens, credentials, banking files, or medical records.
- Policy checks are local text analysis only and do not execute commands.
- Destructive command patterns are blocked by policy checks.
- Restore operations require explicit `--confirm`.
- The dashboard does not reveal redacted sensitive values.
- The experimental MCP server does not expose shell execution or delete operations.
- Retrieval from memory and Strategic Brain is off by default and must be opted in per request or session.

## Roadmap

See `docs/roadmap.md` for implemented modules, intentionally stubbed areas, and v0.4.0 milestones. The next likely areas are stronger approval workflows, richer eval fixtures, formal MCP SDK integration if adopted, strategic brain entity models, and optional backup integrity/encryption.

## Tests

```powershell
pytest
ruff check .
```
