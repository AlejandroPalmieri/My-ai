# Traces

AgentOS Personal writes local JSONL trace events for important CLI operations.

Trace files live under:

```text
.agentos/traces/YYYY-MM-DD.jsonl
```

Each line is one valid JSON object. Trace files are local-only and are intended for debugging, auditability, and future evaluation workflows.

## Event Fields

Each event includes:

- `id`: unique event ID.
- `timestamp`: UTC ISO timestamp.
- `event_type`: structured event name.
- `event`: compatibility alias for `event_type`.
- `command`: CLI command or operation.
- `status`: `started`, `ok`, `failed`, `allow`, `warn`, `block`, or another local status string.
- `project`: optional project name.
- `payload`: structured details.
- `error`: optional error text.

## Event Types

- `command_started`
- `command_completed`
- `command_failed`
- `memory_added`
- `memory_searched`
- `memory_deleted`
- `sdd_created`
- `sdd_phase_advanced`
- `skill_scan_completed`
- `policy_violation`
- `policy_checked`
- `model_request_started`
- `model_request_completed`
- `model_request_failed`
- `model_usage_updated`
- `agent_started`
- `agent_stopped`
- `agent_state_cleared`
- `interactive_message_sent`
- `interactive_message_received`
- `context_warning`
- `context_compacted`

## Redaction

Trace logging redacts sensitive values before writing JSONL. Values matching sensitive terms such as `.env`, private key extensions, SSH key names, `credentials`, `secrets`, `token`, `api_key`, `banking`, or `medical_records` are written as:

```text
[REDACTED]
```

The logger redacts nested payload values and error text. It does not read files or inspect secret contents.

## CLI

```powershell
agentos traces list
agentos traces show --date 2026-06-08
agentos traces tail
agentos traces tail --limit 5
agentos traces export
agentos traces export --date 2026-06-08 --output traces.jsonl
```

`show`, `tail`, and `export` print JSONL lines when no output file is requested.

## Sample

```json
{"command":"memory.add","error":null,"event":"memory_added","event_type":"memory_added","id":"...","payload":{"kind":"note","memory_id":"...","title":"Decision"},"project":"demo","status":"ok","timestamp":"2026-06-08T12:00:00+00:00"}
```
