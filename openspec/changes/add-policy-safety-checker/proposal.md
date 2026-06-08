# Proposal: add-policy-safety-checker

## Summary

Expand the local policy checker into a conservative safety engine that returns `allow`, `warn`, or `block` decisions with reasons and matched rules. The change matters because AgentOS must be able to inspect sensitive paths and dangerous command strings before any future tool orchestration or approval workflow is added.

## Scope

- In scope:
  - Sensitive path detection from `policies/sensitive_paths.yaml`.
  - Destructive command detection from `policies/destructive_commands.yaml`.
  - Approval warning rules from `policies/approval_rules.yaml`.
  - PowerShell destructive command recognition.
  - CLI commands: `policies check`, `policies list`, and `policies explain`.
  - Unit and CLI smoke tests.
  - `docs/security.md`.
- Out of scope:
  - Executing checked commands.
  - Reading secret files.
  - Autonomous approval flows.
  - Full shell parsing or sandbox enforcement.

## Risks

- Risk: Text matching can overblock safe inputs or miss obscure command spellings.
  - Mitigation: Use conservative defaults, document scope, and keep policy files editable.
- Risk: Policy checks could accidentally read secrets.
  - Mitigation: Path checks analyze only the path string and do not open files.
- Risk: Dangerous command examples could be accidentally executed during tests.
  - Mitigation: Tests pass command strings to the checker only; no shell execution is used for dangerous examples.
