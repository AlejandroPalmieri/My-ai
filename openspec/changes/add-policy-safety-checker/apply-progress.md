# Apply Progress: add-policy-safety-checker

## Changes Applied

- Rebuilt `PolicyChecker` around severity-based `PolicyResult` and `PolicyRule` models.
- Added defaults for sensitive path patterns, destructive command patterns, and approval warning rules.
- Added `approval_rules.yaml`.
- Added CLI output for severity, matched rule, and reason.
- Added `agentos policies list` and `agentos policies explain`.
- Added `docs/security.md`.
- Expanded unit and CLI smoke tests.

## Open Issues

- None known.
