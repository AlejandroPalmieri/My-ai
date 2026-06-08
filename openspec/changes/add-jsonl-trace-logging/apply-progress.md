# Apply Progress: add-jsonl-trace-logging

## Changes Applied

- Replaced the simple trace logger with structured JSONL events.
- Added event IDs, event type enum, command/status/project/payload/error fields, and compatibility `event` alias.
- Added sensitive value redaction before serialization.
- Added trace file listing, reading, tailing, and export helpers.
- Added `agentos traces list/show/tail/export`.
- Updated important CLI operations to emit specific trace events.
- Added trace tests and CLI smoke tests.
- Added `docs/traces.md` and updated README/architecture/status/roadmap docs.

## Open Issues

- None known.
