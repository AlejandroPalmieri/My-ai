# Add Interactive Model Chat

## Problem

The no-subcommand `agentos` startup path renders the banner/dashboard, but the
interactive loop only supports a few static commands. It should become a local
model chat loop while preserving safety boundaries.

## Proposal

Add a testable interactive chat session that parses slash commands, keeps
session-only conversation history, sends explicit user messages to the active
model profile, tracks context usage, and supports model/usage/dashboard/agents
commands.

## Non-Goals

- No retrieval-augmented chat yet.
- No automatic inclusion of memory, brain documents, traces, or files.
- No autonomous command execution.

## Safety

Only the user's typed message, optional session system prompt, and current
conversation history are sent to the model. Technical memory search is explicit
and does not add results to model prompts.
