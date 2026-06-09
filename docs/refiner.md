# Controlled Refiner

The controlled refiner is a local analysis layer inspired by Continual Harness.
It reads AgentOS trace JSONL files and proposes improvements, but it does not
modify production behavior.

Commands:

```powershell
agentos refiner analyze
agentos refiner propose
agentos refiner list-proposals
```

`analyze` inspects recent trace events and reports:

- repeated `command_failed` events grouped by command;
- frequent `policy_violation` events grouped by matched rule;
- `memory_searched` events where `result_count` is zero.

`propose` writes a markdown proposal under:

```text
.agentos/refiner/proposals/
```

Each proposal includes the findings, recommendations, and this safety boundary:
human approval is required before any implementation.

## Safety

The refiner must not auto-edit:

- `AGENTS.md`
- skills
- policies
- source code

It only creates proposal markdown files. A future phase may add approval
workflows, but v0 intentionally has no self-modifying behavior and no autonomous
shell execution.

Example proposal excerpt:

```text
### repeated_command_failures

- Severity: warn
- Subject: memory.search
- Count: 2
- Recommendation: Review command error handling, CLI validation, and documentation for this path.
```
