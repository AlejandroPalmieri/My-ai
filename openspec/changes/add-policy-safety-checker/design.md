# Design: add-policy-safety-checker

## Architecture

`src/agentos/policies/checker.py` owns policy models, default rules, YAML list loading, path matching, command matching, rule listing, and explanations. `LocalPolicyService` exposes that behavior through the existing local service boundary. `agentos policies ...` commands format results for terminal output and never execute checked command text.

## Interfaces

- `PolicySeverity`: `allow`, `warn`, `block`.
- `PolicyResult`: `severity`, `reason`, `matched_rule`, `rule_type`, and compatibility property `allowed`.
- `PolicyRule`: `rule_type`, `pattern`, `severity`, `reason`, and `source`.
- `PolicyChecker.check_path(path: str) -> PolicyResult`.
- `PolicyChecker.check_command(command: str) -> PolicyResult`.
- `PolicyChecker.list_rules() -> list[PolicyRule]`.
- `PolicyChecker.explain() -> str`.
- CLI:
  - `agentos policies check --path <path>`
  - `agentos policies check --command <command>`
  - `agentos policies list`
  - `agentos policies explain`
- Policy files:
  - `sensitive_paths.yaml` uses `sensitive_paths`.
  - `destructive_commands.yaml` uses `destructive_commands`.
  - `approval_rules.yaml` uses `approval_commands`.

## Safety

The checker only analyzes strings. It does not open paths, inspect file contents, execute commands, mutate policy files during checks, or invoke shell APIs. Sensitive path and destructive command matches return `block`; approval rules return `warn`; unmatched inputs return `allow`.
