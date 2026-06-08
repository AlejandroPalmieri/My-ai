# Skills

AgentOS Personal supports project-local skills and Codex-style skills.

## Locations

The registry scans both locations:

```text
skills/**/SKILL.md
.agents/skills/**/SKILL.md
```

Project-local skills use scope `project`. Codex-style skills under `.agents/skills` use scope `codex`.

## Frontmatter

Every `SKILL.md` must start with YAML frontmatter:

```markdown
---
name: skill-name
description: Clear description of when this skill should trigger.
---
```

Missing `name` or `description` is reported by validation. AgentOS does not execute scripts from skill folders and does not load full skill content unless `agentos skills show <skill-name>` is used.

## Commands

```powershell
agentos skills scan
agentos skills list
agentos skills show sqlite-memory
agentos skills validate
```

`agentos skills scan` writes:

```text
.agentos/skill-registry.json
```

Each registry entry includes:

```text
name
description
path
scope
last_modified
valid
errors
```

If duplicate skill names exist, AgentOS preserves both entries and emits a warning.

## Codex Invocation

In Codex, invoke a skill by naming it directly in the task when relevant. Examples:

```text
Use the sqlite-memory skill to review this storage change.
Use sdd-workflow before implementing this non-trivial change.
Use safety-review before deleting or pushing files.
```

The registry is metadata only. The full `SKILL.md` body is loaded only when a user or agent explicitly requests `agentos skills show <skill-name>` or asks Codex to use that skill.
