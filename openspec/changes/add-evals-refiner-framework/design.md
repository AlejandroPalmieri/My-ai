# Design: add-evals-refiner-framework

## Architecture

- `src/agentos/evals/runner.py` owns eval execution and JSON result writing.
- `src/agentos/refiner/analyzer.py` owns trace analysis and returns structured findings.
- `src/agentos/refiner/proposals.py` owns markdown proposal rendering and listing.
- CLI handlers remain thin and call the eval runner or `RefinerService`.

## Interfaces

- `EvalRunner(root).run()` returns an `EvalReport` and writes JSON to `.agentos/evals/results/`.
- `TraceRefiner(root).analyze()` returns a `RefinerAnalysis`.
- `ProposalWriter(root).write(analysis)` writes markdown to `.agentos/refiner/proposals/`.
- CLI:
  - `agentos eval run`
  - `agentos refiner analyze`
  - `agentos refiner propose`
  - `agentos refiner list-proposals`

## Safety

- Evals use local isolated workspaces and do not execute checked commands.
- Refiner reads trace logs only.
- Refiner does not edit `AGENTS.md`, skills, policies, or source code.
- Proposals require future human approval before implementation.
