# SDD/OpenSpec Workflow

AgentOS Personal uses a local SDD/OpenSpec workflow for non-trivial changes. It is inspired by Gentle-AI and gentle-pi, but it stays local and does not call external services.

## Commands

```powershell
agentos sdd new add-memory-update
agentos sdd list
agentos sdd status add-memory-update
agentos sdd advance add-memory-update --phase explore
agentos sdd advance add-memory-update --phase proposal
agentos sdd archive add-memory-update
```

Use `--force` only when intentionally skipping phases:

```powershell
agentos sdd advance add-memory-update --phase design --force
```

## Change Name Rules

Change names must be slugs:

- lowercase letters
- numbers
- single hyphens between words

Valid:

```text
add-memory-update
phase-2-sdd
```

Invalid:

```text
Add Memory
bad_slug
bad--slug
```

## Directory Structure

```text
openspec/
  specs/
  changes/
    <change-name>/
      proposal.md
      design.md
      tasks.md
      apply-progress.md
      verify-report.md
      sync-report.md
      metadata.json
```

## Phases

The workflow phases are:

```text
init
explore
proposal
spec
design
tasks
apply
verify
sync
archive
```

By default, a change can only advance to the next phase. This prevents accidental jumps from `init` directly to `apply`. Use `--force` for intentional exceptions.

## Verification Evidence

`verify-report.md` includes TDD sections:

```text
RED
GREEN
TRIANGULATE
REFACTOR
```

Use these sections to record failing tests, passing implementation, additional cases, and refactoring evidence.

## Archive Behavior

`agentos sdd archive <change-name>` marks the change as archived in `metadata.json`. It does not delete or move files. This preserves the local audit trail.
