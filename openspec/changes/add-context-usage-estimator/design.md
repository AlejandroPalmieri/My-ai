# Design

## Context Package

`src/agentos/context/` provides:

- `schemas.py`: `ContextUsage`, `CompactionResult`, and status literals.
- `estimator.py`: conservative character-based token estimation and
  `ContextUsage` assembly.
- `compactor.py`: session-history compaction by dropping oldest messages.

## Estimation

Provider-reported token counts are accepted when available. Otherwise the
estimator uses a conservative character heuristic. Unknown or zero context
windows produce `status=unknown` and `used_percent=None`.

## Thresholds

- `<80%`: `ok`
- `>=80%`: `warn`
- `>=95%`: `critical`

## Integration

Interactive chat uses the estimator and compactor for session-only
conversation history. Dashboard data carries a `ContextUsage` instance so the
bottom status bar and plain dashboard render the same context state.
