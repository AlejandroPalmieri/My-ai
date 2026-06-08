# AgentOS Personal  Codex Working Instructions

## Project goal

Build a modular personal AI agent operating system inspired by:

- Hermes Agent: agent runtime, tool orchestration, subagents, model routing, terminal workflows.
- Engram: local technical memory using SQLite/FTS5.
- GBrain: strategic knowledge layer, retrieval, synthesis, graph-style entities.
- Continual Harness: trajectory analysis, evaluation, and controlled self-improvement.
- Gentle-AI / gentle-pi: SDD/OpenSpec workflows, skill registry, guardrails, TDD evidence, backups, model routing.

The first milestone is not to implement everything. The first milestone is a clean, tested MVP foundation.

## Core principles

1. Prefer small, testable modules.
2. Do not create a giant monolithic agent.
3. Use MCP-compatible boundaries where possible.
4. Local-first by default.
5. Security-first: never read secrets automatically.
6. No destructive command without explicit approval.
7. Every important architectural decision must be documented.
8. Every code change must have tests when practical.
9. Use SDD/OpenSpec flow for non-trivial changes.
10. Keep the MVP simple but extensible.

## MVP scope

Implement the following modules first:

- CLI app.
- Project configuration loader.
- SQLite technical memory.
- Memory search using SQLite FTS5 if available.
- SDD/OpenSpec artifact generator.
- Skill registry scanner.
- Basic policy/permissions loader.
- Logging.
- Pytest test suite.
- Developer documentation.

Do not implement LLM provider integrations in the first pass.
Do not implement autonomous command execution yet.
Do not implement full GBrain-style vector search yet.
Do not implement self-modifying prompts yet.
Create interfaces/stubs for later expansion.

## Preferred stack

- Python 3.11+
- Typer for CLI
- Rich for terminal output
- Pydantic for schemas
- SQLite for local storage
- pytest for tests
- ruff for linting
- mypy optional, but structure code with type hints

## Repository structure target

agentos-personal/
 src/
    agentos/
        cli/
        config/
        memory/
        sdd/
        skills/
        policies/
        logging/
        utils/
 skills/
 openspec/
    specs/
    changes/
 policies/
 tests/
 docs/
 AGENTS.md
 pyproject.toml
 README.md
 .gitignore

## Security rules

Never read or print:

- .env
- private keys
- SSH keys
- API tokens
- credentials
- medical records
- banking files
- secrets directories

Never execute destructive commands without explicit approval:

- rm -rf
- git push --force
- database drop/reset
- chmod/chown recursively
- deleting user files
- rotating credentials
- modifying system-level config

## Testing rules

For every implemented module:

- Add unit tests.
- Add at least one CLI smoke test when relevant.
- Run pytest before declaring completion.
- If tests fail, explain the failure and fix it.

## Documentation rules

Update README.md when adding user-facing commands.
Update docs/architecture.md for architectural decisions.
Create docs/roadmap.md if it does not exist.
Document what is implemented and what is intentionally left as a stub.

## Implementation style

Before editing, inspect the current repository.
After editing, summarize:

- files created
- files modified
- tests run
- tests passed/failed
- next recommended task
