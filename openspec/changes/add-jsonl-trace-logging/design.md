# Design: add-jsonl-trace-logging

## Architecture

`src/agentos/logging/traces.py` owns the trace schema, logger, redaction, daily path calculation, JSONL readers, tail helper, and export helper. CLI commands call `TraceLogger` through `_start_trace`, `_complete_trace`, and `_fail_trace` helpers in `src/agentos/cli/app.py`.

The `traces` Typer group reads local JSONL files and prints raw JSONL for `show`, `tail`, and `export` so output remains machine-readable.

## Interfaces

- `TraceEventType`: enum of supported event types.
- `TraceEvent`: structured event model.
- `TraceLogger.log_event(...) -> TraceEvent`.
- `list_trace_files(root) -> list[str]`.
- `read_trace_events(root, trace_date) -> list[TraceEvent]`.
- `tail_trace_events(root, limit) -> list[TraceEvent]`.
- `export_trace_lines(root, trace_date=None) -> list[str]`.
- CLI:
  - `agentos traces list`
  - `agentos traces show --date YYYY-MM-DD`
  - `agentos traces tail`
  - `agentos traces export`

## Safety

Trace logging redacts sensitive-looking strings and sensitive keys before writing. It does not read secret files or inspect file contents. Trace commands only read local trace files under `.agentos/traces` and optionally write an explicit export file when `--output` is provided.
