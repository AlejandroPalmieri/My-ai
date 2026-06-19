# Streaming Chat

AgentOS can stream model responses for one-shot chat and interactive chat. Streaming sends only the explicit user message and optional system prompt; it does not automatically include files, memory, brain documents, traces, or secrets.

## Quick Path

Use streaming for a single prompt:

```powershell
agentos chat once "hello streaming" --stream
agentos chat once "hello streaming" --stream --model local-stub
agentos chat once "hello streaming" --stream --effort high
```

Disable streaming explicitly:

```powershell
agentos chat once "hello streaming" --no-stream
```

## Interactive Chat

Interactive chat streams normal messages by default when the active provider supports streaming.

```powershell
agentos
/stream status
/stream off
/stream on
```

## Provider Behavior

| Provider | Streaming behavior |
|----------|--------------------|
| `local-stub` | Supports deterministic fake streaming for tests and offline use. |
| `openai` / `openai_compatible` / `openrouter` | Uses OpenAI-compatible server-sent chat completion events when configured. |
| `anthropic` | Uses Anthropic streaming messages when configured. |
| `ollama` | Streams from the local Ollama API when the local server supports it. |
| Unsupported providers | Fall back to non-streaming completion. |

AgentOS normalizes provider stream events into `message_start`, `content_delta`, `message_done`, `usage_delta`, and `error`.

## Usage And Traces

Token usage is recorded after streaming completes. If a provider returns usage at the end, AgentOS uses it. If usage is absent, AgentOS estimates tokens locally.

Streaming traces include metadata-only events:

- `stream_started`
- `stream_delta_received`
- `stream_completed`
- `stream_failed`

Trace payloads do not store full prompt or full response bodies by default.

## Release Checkpoint

v0.3.0 treats streaming as part of the provider boundary, not a CLI-only feature.
Adapters emit normalized events so CLI, interactive chat, evals, and usage
accounting can share the same stream handling path.
