# Design

## Storage

Agent runtime state is a local JSON file:

```text
.agentos/agents/runtime-state.json
```

The file stores a list of agent records. The registry owns read/write behavior
and keeps active agents first when listing.

## Agent Record

Each record includes id, name, role, kind, status, model profile, effort,
optional parent id, task summary, timestamps, token counters, and estimated
cost.

## CLI

`agentos agents start` writes a runtime record and trace event, but does not
execute work. `stop` marks a record completed. `clear` requires `--confirm`.

## UI

The right dashboard pane becomes `Agents / Subagents`. It shows active agents
first and includes a compact `Runtime` section below the agent list.
