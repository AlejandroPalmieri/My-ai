# Apply Progress: add-project-profiles

## Changes Applied

- Replaced the minimal profile model with full profile fields, built-in profile
  definitions, active profile switching, and profile validation.
- Added `agentos profile init/list/show/set/validate`.
- Updated `agentos init` to create `.agentos/profile.yaml` with default
  profiles.
- Updated `memory add` to use the active profile's `memory_project` when
  `--project` is omitted.
- Extended local policy checks with active profile `blocked_paths`.
- Added nested directory matching support for profile blocked path rules.
- Added unit and CLI smoke tests for profile initialization, set/show,
  validation warnings, memory default project behavior, and profile policy
  additions.
- Added `docs/profiles.md` and README examples.

## Open Issues

- None for the requested scope.
