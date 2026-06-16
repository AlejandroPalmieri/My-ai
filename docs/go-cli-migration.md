# Go CLI Migration

AgentOS is moving toward a Go CLI incrementally. The Python CLI remains the full-featured runtime while Go takes over stable, performance-sensitive command boundaries one slice at a time.

## Quick Path

Install the Go CLI from source:

```sh
curl -fsSL https://raw.githubusercontent.com/AlejandroPalmieri/My-ai/main/scripts/install.sh | sh
```

Verify the install:

```sh
agentos version
agentos doctor
```

## Current Scope

| Area | Status |
|------|--------|
| `agentos version` | Implemented in Go |
| `agentos doctor` | Implemented in Go for local Go CLI checks |
| `agentos init` | Implemented in Go for base directories and policy files |
| Full memory, dashboard, models, chat, SDD workflow | Still handled by Python |

## Migration Rule

Keep each migrated command behavior-compatible before removing Python code. The Go CLI should grow by small command slices with tests, not by a full rewrite.
