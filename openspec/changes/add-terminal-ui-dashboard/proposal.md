# Proposal: add-terminal-ui-dashboard

## Summary

Add a neutral AgentOS startup intro and a Rich-based, Zellij-inspired read-only
terminal dashboard for no-subcommand startup. This gives the CLI a professional
local runtime surface without adding external services or a full TUI framework.

## Scope

- In scope:
  - `agentos` startup banner and dashboard.
  - Root startup flags: `--no-banner`, `--no-dashboard`, `--plain`, `--theme`.
  - `agentos dashboard --theme zellij-neutral`.
  - `agentos ui preview/themes/set-theme/banner`.
  - `.agentos/config.yaml` UI settings.
  - Built-in `zellij-neutral` theme.
  - Tests for theme loading, banner rendering, dashboard data assembly, and CLI smoke.
- Out of scope:
  - Textual dependency.
  - Interactive pane switching.
  - External services.
  - Gentle-AI rose/pink branding or persona.

## Risks

- Risk: Rich layout output can vary by terminal width, so tests assert stable
  content rather than exact border rendering.
- Risk: dashboard data could accidentally expose content; this change renders
  memory metadata only and tests that memory content is omitted.
