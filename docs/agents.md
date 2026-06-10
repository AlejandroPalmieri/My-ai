# Agent Runtime Registry

AgentOS includes a local runtime registry for agents and subagents:

```text
.agentos/agents/runtime-state.json
```

This is state tracking only. Starting an agent writes a local metadata record;
it does not run shell commands, call an LLM, start a background worker, or
perform autonomous work.

## Commands

```powershell
agentos agents start --name Planner --role planning --task "Plan the next change" --model local-stub
agentos agents start --name Researcher --role research --task "Inspect docs" --model local-stub --kind subagent --parent-id <agent-id>
agentos agents list
agentos agents status
agentos agents stop <agent-id>
agentos agents clear --confirm
```

`agents clear` requires `--confirm` because it removes the local runtime state
file contents.

## Fields

Each runtime record stores:

- `id`
- `name`
- `role`
- `kind`: `agent` or `subagent`
- `status`: `idle`, `running`, `waiting`, `completed`, or `failed`
- `model_profile`
- `effort`
- `parent_id`
- `current_task`
- `started_at`
- `updated_at`
- `input_tokens`
- `output_tokens`
- `estimated_cost_usd`

## Traces

Agent lifecycle commands write local trace events:

- `agent_started`
- `agent_stopped`
- `agent_state_cleared`

They do not write `model_request_started` unless a future explicit model call
is added.

## Dashboard

The right-side dashboard pane is titled `Agents / Subagents`. It lists active
agents first, then recently completed entries, and includes a compact runtime
section below the agent list.

If usage events include an `agent_id`, the pane shows token and estimated cost
totals from `.agentos/usage/usage.db`. Starting an agent still does not call a
model; usage totals only appear after an explicit future operation records
tokens for that agent.
