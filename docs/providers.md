# Model Providers

AgentOS uses provider-specific adapters behind one chat boundary. `local-stub` remains the default offline provider; real providers use environment variable names only and never store API key values in `.agentos/models.yaml`.

## Quick Path

Inspect configured providers:

```powershell
agentos models providers
agentos models provider-status
agentos models test local-stub
agentos models test local-stub --stream
```

## Supported Providers

| Provider | API key env | Streaming | Notes |
|----------|-------------|-----------|-------|
| `local-stub` | none | yes | Offline deterministic responses for tests and local smoke checks. |
| `openai` | `OPENAI_API_KEY` | yes | Uses OpenAI `/chat/completions` compatible shape. |
| `openai-compatible` | configurable | yes when compatible | Uses `base_url` and `api_key_env` from config. |
| `openrouter` | `OPENROUTER_API_KEY` | yes | Defaults to `https://openrouter.ai/api/v1`; safe extra headers only. |
| `anthropic` | `ANTHROPIC_API_KEY` | yes | Uses Anthropic messages API shape through `httpx`. |
| `ollama` | none | yes when local server supports it | Defaults to local Ollama OpenAI-compatible endpoint. |

## Setup Examples

OpenAI:

```powershell
$env:OPENAI_API_KEY = "..."
agentos models set openai-gpt-5-5
agentos models test openai-gpt-5-5
```

OpenRouter:

```powershell
$env:OPENROUTER_API_KEY = "..."
agentos models set openrouter-auto
agentos models test openrouter-auto --stream
```

Anthropic:

```powershell
$env:ANTHROPIC_API_KEY = "..."
agentos models set anthropic-claude-sonnet
agentos models test anthropic-claude-sonnet
```

Ollama:

```powershell
ollama serve
agentos models set ollama-local
agentos models test ollama-local
```

## Error Codes

Provider failures normalize to:

- `missing_api_key`
- `network_error`
- `auth_error`
- `rate_limit`
- `invalid_model`
- `provider_error`
- `unsupported_feature`

## Dependency Choice

AgentOS uses `httpx`, already present in project dependencies, for provider HTTP calls. No provider SDK is required for this adapter layer.
