# Proposal: add-interactive-dashboard-actions

## Summary

Add interactive dashboard controls that remove the static/read-only dashboard
limitations while preserving AgentOS safety boundaries.

## Scope

- In scope:
- Keyboard pane focus for overview, memory, SDD, policies, traces, and runtime context.
- Refresh action.
- Safe local actions for backup creation, skill scan, and eval run.
- `agentos dashboard --interactive` and `--once` test mode.
- Safe explanation for redacted policy values.
- Out of scope:
- Textual dependency.
- Arbitrary shell execution.
- Revealing sensitive or redacted policy values.
- Destructive restore/delete actions.

## Risks

- Risk: Interactive actions could become an unsafe command launcher.
  Mitigation: Only call local AgentOS service APIs; no shell execution.
- Risk: Users may expect redacted secrets to be revealed.
  Mitigation: Keep redaction intact and provide a safe explanation action.
