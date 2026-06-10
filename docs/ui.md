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
  policies, SDD status, and model runtime status.
- Zellij-inspired dashboard with top status bar, pane borders, focused pane
  emphasis, navigation, workspace overview, an `Agents / Subagents` right pane,
  runtime context, and bottom keybar.

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
chat:
  max_history_messages: 20
```

The built-in theme is `zellij-neutral`. It uses a neutral dark palette with
teal-focused active borders and no persona or branded rose/pink styling.

## Data Displayed

The dashboard displays compact local metadata:

- Active model, provider, effort, context usage, cumulative token totals, and
  estimated cost from local model configuration.
- Active and recently active agents/subagents from
  `.agentos/agents/runtime-state.json`.
- Recent memory title, project, and kind.
- Active SDD change names and phases.
- Recent trace event type, command, and status.
- Local paths for memory database, skill registry, and policy files.

Memory content is not rendered in the dashboard. The model status bar and agent
pane read local metadata only; they do not send prompts, execute commands, or
load local files into any provider.
If `.agentos/models.yaml` is missing, the dashboard falls back to the default
`local-stub` profile. The context percentage is backed by
`agentos.context.ContextUsage`; unknown context windows render as `ctx: n/a`.
Warn and critical context states use warning/danger styling in Rich terminals.
Unknown pricing renders as `cost: n/a`.

The bottom bar uses two local status zones:

```text
[q] quit | [tab] pane | [r] refresh | [b] backup | [e] eval | [k] scan skills | [m/s/p/t] focus
model: local-stub|provider: local|effort: low|ctx: 0.00%|tok: 0/10.0k|i/o/t: 0/0/0|cost: $0.000000
```

In compact mode, the model/runtime zone is shortened to:

```text
model: local-stub | effort: low | ctx: 0.00% | cost: $0.000000
```

Example right pane:

```text
Agents / Subagents
AGENTS
Planner  agent | running | planning | local-stub | high tok=0/0 cost=n/a
task     Plan dashboard agent pane

RUNTIME
active profile  default
model           local-stub
```
