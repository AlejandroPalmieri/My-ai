# Design

## Session Boundary

`InteractiveChatSession` owns parser behavior, session history, local context
accounting, and command results. `run_interactive_cli` stays responsible for
console IO and dashboard rendering.

## Context Handling

The session estimates tokens from:

- system prompt
- conversation history
- latest user message
- latest assistant response

If context exceeds 80 percent, the UI warns. If it exceeds 95 percent or
history exceeds the configured limit, the oldest messages are dropped with a
visible compaction notice and trace event.

## Configuration

`.agentos/config.yaml` gains:

```yaml
chat:
  max_history_messages: 20
```

## Traces

Interactive chat writes:

- `interactive_message_sent`
- `interactive_message_received`
- `context_warning`
- `context_compacted`
