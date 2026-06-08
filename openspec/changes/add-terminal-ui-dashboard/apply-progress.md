# Apply Progress: add-terminal-ui-dashboard

## Changes Applied

- Added `agentos.ui` package with theme, banner, dashboard, and layout modules.
- Added `.agentos/config.yaml` UI settings with defaults created by `agentos init`.
- Updated no-subcommand startup to render the banner/dashboard before the
  existing interactive prompt.
- Added `dashboard` and `ui` CLI commands.
- Added startup flags for banner, dashboard, plain output, and theme selection.
- Added tests for theme loading, banner rendering, dashboard data assembly, CLI
  startup flags, and UI theme listing.
- Added `docs/ui.md` and updated README, architecture, roadmap, implementation
  status, and Windows PowerShell docs.

## Open Issues

- None for the requested read-only dashboard scope.
