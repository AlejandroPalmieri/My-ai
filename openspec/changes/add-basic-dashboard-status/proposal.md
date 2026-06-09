# Proposal: add-basic-dashboard-status

## Summary

Expand the existing read-only terminal dashboard so it covers the basic local
AgentOS status requested for daily PowerShell use.

## Scope

- In scope:
- Show active profile, memory count, recent memories, active SDD changes,
  registered skills, recent policy violations, and latest trace events.
- Keep the dashboard Rich-based with plain text fallback.
- Add dashboard data assembly tests and CLI smoke coverage.
- Out of scope:
- Interactive pane switching.
- Textual dependency.
- External services or command execution.

## Risks

- Risk: Dashboard could expose sensitive policy paths from traces.
  Mitigation: Use already-redacted trace payloads and do not read secret files.
- Risk: Dashboard data collection could mutate registry state.
  Mitigation: Discover skill summaries read-only when registry is missing.
