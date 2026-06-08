# Proposal: add-interactive-default

## Summary

Make `agentos` without a subcommand start a safe local interactive CLI. Unknown root-level options should be forwarded to that interactive CLI instead of failing command parsing. This prepares the command surface for future model/profile/runtime options without implementing provider integrations or autonomous execution.

## Scope

- In scope:
  - Add a console-script entrypoint wrapper before raw Typer parsing.
  - Add a small interactive CLI loop with `help`, `version`, `doctor`, and `exit`.
  - Forward no-subcommand options to the interactive CLI.
  - Keep existing subcommands routed through Typer unchanged.
  - Add tests for no-subcommand startup and option forwarding.
  - Update documentation.
- Out of scope:
  - LLM provider calls.
  - Autonomous command execution.
  - Agent runtime orchestration.
  - Full terminal shell behavior inside the interactive CLI.

## Risks

- Risk: Unknown options for real subcommands could be swallowed by interactive dispatch.
  - Mitigation: Dispatch to Typer whenever the first non-root token is a known top-level subcommand.
- Risk: Interactive mode could imply unsafe autonomous behavior.
  - Mitigation: Keep the loop read-only and limited to static commands plus pointers to existing CLI commands.
