# Safe Tools

AgentOS tools v0 are internal Python functions behind an allowlist. They are not
shell commands, file readers, file writers, or network browsers.

## Commands

```powershell
agentos tools list
agentos tools show memory_search
agentos tools test policies_check --json-input '{"command":"pytest"}'
```

## Built-In Tools

- `memory_search`: search technical memory excerpts.
- `memory_add`: add a technical memory after explicit approval.
- `brain_search`: search Strategic Brain excerpts.
- `sdd_new`: create an SDD/OpenSpec change after explicit approval.
- `sdd_status`: show one SDD change or list changes.
- `skills_list`: list skill metadata.
- `policies_check`: check one path or command string.
- `usage_summary`: show local usage totals.

## Safety Model

Each tool declares:

- `name`
- `description`
- `input_schema`
- `output_schema`
- `risk_level`: `safe`, `review`, or `blocked`
- `requires_approval`
- `max_calls_per_run`

The executor blocks unknown tools, blocked tools, missing required arguments,
dangerous arguments, and tools requiring approval unless the caller explicitly
passes approval.

There is no `shell`, file read/write, or network browsing tool in v0.

## Traces

Tool execution writes local trace events:

- `tool_call_requested`
- `tool_call_allowed`
- `tool_call_blocked`
- `tool_call_completed`
- `tool_call_failed`

Trace payloads include tool names and status metadata, not secrets.
