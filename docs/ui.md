# Terminal UI

AgentOS Personal includes a local Rich-based startup UI. It is read-only and
does not call external services.

## Startup

Run the executable with no subcommand:

```powershell
agentos
```

Startup renders:

- `AGENTOS` text logo.
- `Personal Agent Operating System` subtitle.
- Runtime panel with version, active profile, workspace, memory, skills,
  policies, and SDD status.
- Zellij-inspired dashboard with top status bar, pane borders, focused pane
  emphasis, navigation, workspace overview, runtime context, and bottom keybar.

The current dashboard is intentionally read-only. It does not implement pane
switching yet.

## Flags

```powershell
agentos --no-banner
agentos --no-dashboard
agentos --plain
agentos --theme zellij-neutral
agentos dashboard --theme zellij-neutral
```

`--plain` uses plain text output for terminals where Rich color/layout output is
not appropriate. Narrow terminals use the compact layout automatically.

## Commands

```powershell
agentos ui preview
agentos ui themes
agentos ui set-theme zellij-neutral
agentos ui banner --show
agentos ui banner --hide
```

## Configuration

`agentos init` creates `.agentos/config.yaml`:

```yaml
ui:
  show_banner: true
  open_dashboard_on_start: true
  theme: zellij-neutral
  compact_mode: auto
```

The built-in theme is `zellij-neutral`. It uses a neutral dark palette with
teal-focused active borders and no persona or branded rose/pink styling.

## Data Displayed

The dashboard displays compact local metadata:

- Recent memory title, project, and kind.
- Active SDD change names and phases.
- Recent trace event type, command, and status.
- Local paths for memory database, skill registry, and policy files.

Memory content is not rendered in the dashboard.
