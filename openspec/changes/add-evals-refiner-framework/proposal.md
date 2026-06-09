# Proposal: add-evals-refiner-framework

## Summary

Add a safe local evaluation runner and controlled refiner framework. The goal is
to start collecting repeatable quality evidence and trace-derived improvement
ideas without adding autonomous self-modifying behavior.

## Scope

- In scope:
- Local eval runner for memory search, policy checks, skill validation, and SDD workflow.
- JSON eval result reports under `.agentos/evals/results/`.
- Trace refiner analysis for repeated command failures, frequent policy violations, and failed memory searches.
- Markdown proposal generation under `.agentos/refiner/proposals/`.
- CLI commands for `agentos eval run` and `agentos refiner ...`.
- Out of scope:
- LLM synthesis, embeddings, external services, autonomous code edits, and approval automation.

## Risks

- Risk: Eval workspaces can leave local files behind.
  Mitigation: Keep them scoped under `.agentos/evals/workspace/` for auditability and Windows SQLite stability.
- Risk: Refiner output could be mistaken for approved changes.
  Mitigation: Proposal files explicitly state that human approval is required.
