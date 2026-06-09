# Design: add-interactive-dashboard-actions

## Architecture

- `src/agentos/ui/interactive.py` owns dashboard interaction state and key handling.
- `DashboardController` is testable without a terminal loop.
- `run_interactive_dashboard` handles terminal rendering and key reads.
- Existing dashboard data assembly and render functions are reused.

## Interfaces

- `DashboardController(root).handle_key(key)` returns a `DashboardActionResult`.
- `agentos dashboard --interactive` starts keyboard controls.
- `agentos dashboard --interactive --once` renders the interactive shell once for smoke tests.
- Keys:
  - `tab`/`n`: next pane.
  - `m`, `s`, `p`, `t`, `o`: focus panes.
  - `r`: refresh.
  - `b`: create backup.
  - `k`: scan skills.
  - `e`: run evals.
  - `u`: explain redaction.
  - `q`: quit.

## Safety

- No shell commands are executed from the dashboard.
- Backup creation, skill scanning, and eval runs use local service APIs.
- Redacted policy values remain redacted.
- Restore, delete, prune, and other destructive actions are not exposed in the dashboard.
