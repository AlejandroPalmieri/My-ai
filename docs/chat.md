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
agentos chat once "message" --system "Reply briefly."
agentos chat once "message" --json
agentos chat status
```

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

Trace payloads include provider/model metadata and token counts, not prompt
text or API key values.

## Limitations

- No streaming yet.
- No tool calling yet.
- No autonomous agent or subagent execution.
- No automatic memory or file retrieval.
- OpenAI-compatible support is `/chat/completions` only.
- If provider usage is missing, AgentOS estimates tokens locally.
