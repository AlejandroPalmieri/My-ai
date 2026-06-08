# Design: add-terminal-ui-dashboard

## Architecture

The UI is split into small modules:

- `agentos.ui.theme`: built-in theme metadata and palette loading.
- `agentos.ui.banner`: startup banner rendering.
- `agentos.ui.dashboard`: dashboard data collection and render entrypoint.
- `agentos.ui.layout`: Rich pane layout, compact layout, and plain output.
- `agentos.config.settings`: `.agentos/config.yaml` UI settings.

Dashboard data collection is separate from rendering so tests can validate local
runtime state without depending on Rich border formatting.

## Interfaces

CLI:

- `agentos --no-banner`
- `agentos --no-dashboard`
- `agentos --plain`
- `agentos --theme zellij-neutral`
- `agentos dashboard --theme zellij-neutral`
- `agentos ui preview`
- `agentos ui themes`
- `agentos ui set-theme <theme-name>`
- `agentos ui banner --show`
- `agentos ui banner --hide`

Config file:

```yaml
ui:
  show_banner: true
  open_dashboard_on_start: true
  theme: zellij-neutral
  compact_mode: auto
```

## Safety

The dashboard is read-only. It does not execute commands, call external
services, or load full skill content. Memory content is not rendered; only title,
project, kind, and timestamps are used for recent memory summaries.
