# Add Chat Once Client Boundary

## Summary

Add the first model client boundary and a minimal `agentos chat once` command.
The first real runtime path supports an offline `local-stub` provider and a
safe OpenAI-compatible adapter boundary.

## Goals

- Send exactly the user message and optional system prompt to the selected
  model profile.
- Support `local-stub` offline with deterministic responses and token counting.
- Add an OpenAI-compatible provider boundary with clear setup errors when API
  keys or HTTP dependencies are missing.
- Update local usage state and a clearly named `.agentos/model-usage.json`
  usage store.
- Emit model request and usage trace events with redaction.

## Non-Goals

- No autonomous agent execution.
- No automatic memory, file, trace, or secret inclusion.
- No streaming.
- No tool calling.
