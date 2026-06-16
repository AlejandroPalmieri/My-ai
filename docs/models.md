# Model Provider Configuration

AgentOS stores local model/provider metadata in:

```text
.agentos/models.yaml
```

This file is for configuration and inspection only. It does not enable
autonomous agent execution. The separate `agentos chat once` command can use
this metadata for a single explicit prompt.

## Safety Rules

- API keys are never written to `models.yaml`.
- AgentOS stores environment variable names such as `OPENAI_API_KEY`,
  `OPENROUTER_API_KEY`, and `ANTHROPIC_API_KEY`.
- AgentOS does not read `.env` automatically.
- Missing API keys are reported as `not configured`, not as crashes.
- Pricing values are editable estimates. They are not exact current provider
  prices.
- Unknown pricing is stored as `null` and rendered as `n/a`.

## Commands

```powershell
agentos models init
agentos models list
agentos models show
agentos models set local-stub
agentos models status
agentos models usage
agentos models reset-usage --confirm
agentos models effort list
agentos models effort show high
agentos models route list
agentos models route set default_chat --model local-stub --effort medium
agentos chat once "Hello AgentOS"
agentos chat status
```

## Default Profiles

- `local-stub`
- `openai-gpt-5-5-thinking`
- `openai-gpt-5-5`
- `openrouter-auto`
- `ollama-local`

`local-stub` is the default active profile. It works without network access and
without API keys.

## Configuration Shape

```yaml
active:
  active_model_profile: local-stub
  active_provider: local
  active_model: local-stub
  effort: low
  context_window_tokens: 10000
  context_used_tokens: 0
  context_used_percent: 0.0
  cumulative_input_tokens: 0
  cumulative_output_tokens: 0
  cumulative_total_tokens: 0
  cumulative_estimated_cost_usd: 0.0
providers:
  - name: openai
    kind: openai
    base_url: null
    api_key_env: OPENAI_API_KEY
    enabled: true
    supports_streaming: true
model_profiles:
  - name: openai-gpt-5-5
    provider: openai
    model: gpt-5.5
    effort: medium
    context_window_tokens: 128000
    input_token_cost_per_1m: null
    output_token_cost_per_1m: null
    default_temperature: 0.2
    enabled: true
```

## Usage Accounting

The model configuration layer can record local token totals and estimate cost
from the active profile pricing fields. If either input or output pricing is
unknown, cumulative estimated cost remains `n/a`.

Usage accounting is local metadata only. It does not prove that a provider call
occurred.

`agentos chat once` writes cumulative usage to `.agentos/model-usage.json` and
updates the active usage fields in `.agentos/models.yaml`. Successful model
responses also write metadata-only events to `.agentos/usage/usage.db`.

Use:

```powershell
agentos usage summary
agentos usage by-model
agentos usage export --format json
```

See `docs/chat.md` and `docs/usage.md`.

## Streaming Support

Providers declare streaming capability with `supports_streaming`. The default
`local-stub`, `openai`, and `openrouter` providers support streaming. Providers
without streaming support gracefully fall back to non-streaming chat.

```powershell
agentos chat once "hello streaming" --stream --model local-stub
```

See `docs/streaming-chat.md`.

## Effort And Routing

AgentOS also stores local model routing metadata in:

```text
.agentos/model-routing.yaml
```

Routes choose an effort level and can optionally pin a model profile for a
workflow. Defaults include `default_chat: medium`, `coding: high`,
`sdd_verify: max`, and `safety_review: max`.

Explicit CLI effort overrides route defaults:

```powershell
agentos chat once "Quick answer" --effort low
```

See `docs/model-routing.md`.

## Dashboard Status

The startup banner and dashboard bottom bar show the active model profile,
provider, effective chat effort, context usage, cumulative token totals, and
estimated cost from local model metadata. The dashboard also shows current
session and daily estimated cost from the usage database. This display is
read-only and does not contact a provider.

If `.agentos/models.yaml` is missing, AgentOS uses the default `local-stub`
profile so the dashboard can still render. If the active profile has an unknown
context window, the dashboard shows `ctx: n/a`. If pricing is unknown, it shows
`cost: n/a`.
