# Design: add-project-profiles

## Architecture

Profiles live in `src/agentos/config/profiles.py`. The module owns the
`ProfileSpec` and `ProjectProfile` models, default profile definitions, YAML
read/write helpers, active profile switching, and validation.

The CLI reads and writes profiles through the config module. Local services read
the active profile when constructing policy behavior. Memory commands resolve a
missing `--project` value through the active profile's `memory_project`.

## Interfaces

Public CLI commands:

- `agentos profile init`
- `agentos profile list`
- `agentos profile show`
- `agentos profile set <profile-name>`
- `agentos profile validate`

Profile file:

```yaml
active_profile: default
profiles:
  default:
    name: default
    description: General AgentOS work.
    default_project: default
    memory_project: default
    preferred_skills: []
    sdd_required_for: []
    blocked_paths: []
    test_commands:
      - pytest
    notes: General purpose profile.
```

Each profile supports `name`, `description`, `default_project`,
`memory_project`, `preferred_skills`, `sdd_required_for`, `blocked_paths`,
`test_commands`, and `notes`.

## Safety

Profile validation warns on unknown preferred skill names instead of failing, so
planned skills do not block profile use. Profile `blocked_paths` are only used
as local policy checker inputs; no checked command is executed. The policy
service still returns severity, reason, and matched rule for path or command
checks.
