# Proposal: add-project-profiles

## Summary

Add local AgentOS project profiles so one workspace can switch between common
work modes without changing every CLI command manually. Profiles define the
active memory project, preferred skills, SDD expectations, profile-specific
blocked paths, test commands, and notes.

## Scope

- In scope:
  - `.agentos/profile.yaml` generation and parsing.
  - Built-in profiles for default, Godot, bioinformatics, USMLE, Neocircuit,
    and data science.
  - `agentos profile init/list/show/set/validate`.
  - `agentos init` profile creation.
  - Memory add defaulting to the active profile when `--project` is omitted.
  - Profile `blocked_paths` extending local policy checks.
  - Validation warnings for unknown preferred skills.
- Out of scope:
  - Network profile sync.
  - Automatic skill installation.
  - Autonomous command execution.

## Risks

- Risk: profile parsing is intentionally minimal YAML and should stay documented
  until a fuller config parser is introduced.
- Risk: profile-specific blocked paths are conservative and may overblock local
  checks, but they do not execute commands.
