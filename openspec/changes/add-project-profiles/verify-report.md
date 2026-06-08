# Verify Report: add-project-profiles

## RED

- `pytest tests/test_profiles.py` failed because `set_active_profile` and
  validation support were not implemented.
- Profile CLI smoke tests failed because the `profile` command group did not
  exist.
- Memory add profile fallback test failed because omitted `--project` still
  used the hard-coded default project.
- Profile blocked path tests failed because policy services did not include
  active profile additions.

## GREEN

- `pytest tests/test_profiles.py` passed.
- Focused CLI and policy profile tests passed.
- Full suite passed with `52 passed`.
- Ruff passed with `All checks passed`.

## TRIANGULATE

- Covered active profile set/show behavior with `data-science`.
- Covered validation warnings for an unknown preferred skill.
- Covered PowerShell-adjacent policy behavior by extending local policy matching
  rather than executing commands.
- Covered memory add defaulting to `usmle-notes` after setting the USMLE
  profile.

## REFACTOR

- Reused the config profile module for CLI and service behavior instead of
  duplicating profile parsing logic.
- Kept profile validation warning-only for unknown skills to preserve local
  flexibility.
