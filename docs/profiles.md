# Profiles

AgentOS profiles describe local work modes. Profiles live in:

```text
.agentos/profile.yaml
```

`agentos init` and `agentos profile init` create the default profile file when it does not exist.

## Built-In Profiles

- `default`: general AgentOS work.
- `godot`: Godot game development.
- `bioinformatics`: biological data and pipeline work.
- `usmle`: USMLE study and retrieval workflows.
- `neocircuit`: Neocircuit research and synthesis.
- `data-science`: data exploration, modeling, and reporting.

## Fields

Each profile includes:

- `name`
- `description`
- `default_project`
- `memory_project`
- `preferred_skills`
- `sdd_required_for`
- `blocked_paths`
- `test_commands`
- `notes`

## CLI

```powershell
agentos profile init
agentos profile list
agentos profile show
agentos profile set usmle
agentos profile validate
```

`profile validate` treats unknown skill names as warnings, not hard failures. This lets profiles reference future skills while still surfacing configuration drift.

## Memory Defaults

When `agentos memory add` is called without `--project`, AgentOS uses the active profile's `memory_project`.

Example:

```powershell
agentos profile set usmle
agentos memory add --title "Weak area" --content "Review renal physiology."
```

The memory is stored under project `usmle`.

## Profile Policy Additions

The active profile's `blocked_paths` are added to local policy checks. This lets each work mode add extra conservative path blocks without editing global policy files.

Example:

```yaml
blocked_paths:
  - medical_records/
  - patient_notes/
```

These are checked alongside `policies/sensitive_paths.yaml`.
