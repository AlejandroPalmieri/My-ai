# Chat Once

AgentOS includes a minimal single-turn chat boundary:

```powershell
agentos chat once "Hello AgentOS"
```

This command sends only the explicit message and optional system prompt supplied
on the command line. It does not automatically send local files, memories,
traces, databases, policies, or secrets.

## Commands

```powershell
agentos chat once "message"
agentos chat once "message" --model local-stub
agentos chat once "message" --effort low
agentos chat once "message" --stream
agentos chat once "message" --no-stream
agentos chat once "message" --with-memory
agentos chat once "message" --with-brain
agentos chat once "message" --with-memory --memory-query "decision"
agentos chat once "message" --with-brain --brain-query "strategy"
agentos chat once "message" --with-memory --with-brain --show-context
agentos chat once "message" --with-memory --dry-run-context
agentos chat once "message" --system "Reply briefly."
agentos chat once "message" --json
agentos chat status
```

## Streaming

Use `--stream` to print response deltas as they arrive. Use `--no-stream` to
force the regular non-streaming response path.

```powershell
agentos chat once "hello streaming" --stream
agentos chat once "hello streaming" --stream --model local-stub
agentos chat once "hello streaming" --stream --effort high
```

If the active provider does not support streaming, AgentOS falls back to
non-streaming completion. JSON output stays valid: `--json --stream` does not
print raw stream deltas before the JSON payload.

## Explicit Retrieval

Chat does not automatically include memory, Strategic Brain documents, files,
traces, or local data. Use `--with-memory` and/or `--with-brain` to opt in for a
single request. Use `--show-context` to inspect the context before the response,
or `--dry-run-context` to print the context without calling a provider.

See `docs/retrieval.md`.

## Local Stub

`local-stub` is the default active model profile. It works offline, requires no
API key, returns deterministic test-friendly output, estimates token usage, and
updates local usage metadata.

Example:

```powershell
agentos models init
agentos chat once "Summarize AgentOS in one sentence."
agentos models usage
```

## OpenAI-Compatible Providers

OpenAI-compatible providers use `base_url`, `model`, and `api_key_env` from
`.agentos/models.yaml`.

Example OpenRouter-style profile:

```yaml
providers:
  - name: openrouter
    kind: openai_compatible
    base_url: https://openrouter.ai/api/v1
    api_key_env: OPENROUTER_API_KEY
    enabled: true
model_profiles:
  - name: openrouter-auto
    provider: openrouter
    model: auto
    effort: medium
    context_window_tokens: 128000
    input_token_cost_per_1m: null
    output_token_cost_per_1m: null
    default_temperature: 0.2
    enabled: true
```

Set the API key in the environment before calling a real provider:

```powershell
$env:OPENROUTER_API_KEY = "..."
agentos models set openrouter-auto
agentos chat once "Hello"
```

AgentOS does not read `.env` automatically and does not store API key values in
configuration or traces.

## Usage And Traces

Usage is stored in:

```text
.agentos/model-usage.json
```

The active model state in `.agentos/models.yaml` is also updated so the current
status remains easy to inspect.

Trace events emitted by chat:

- `model_request_started`
- `model_request_completed`
- `model_request_failed`
- `model_usage_updated`
- `stream_started`
- `stream_delta_received`
- `stream_completed`
- `stream_failed`
- `retrieval_requested`
- `retrieval_context_built`
- `retrieval_context_sent`
- `retrieval_dry_run`

Trace payloads include provider/model metadata and token counts, not prompt
text or API key values.

## Limitations

- No tool calling yet.
- No autonomous agent or subagent execution.
- No automatic memory or file retrieval.
- OpenAI-compatible support is `/chat/completions` only.
- If provider usage is missing, AgentOS estimates tokens locally.
