# Design

The implementation adds a narrow local model configuration layer:

- `schemas.py` owns Pydantic models.
- `config.py` owns default config creation, tiny YAML rendering/parsing, profile
  activation, and status inspection.
- `registry.py` exposes enabled providers/profiles.
- `pricing.py` calculates editable estimated costs and returns unknown cost as
  `None`.
- `usage.py` records cumulative token usage into the active model state.

`.agentos/models.yaml` is local metadata. API key values are never written and
`.env` is never read. Provider status uses `os.environ` only to check whether
the configured environment variable is present.

The first implementation is configuration and inspection only. It deliberately
does not call OpenAI, Anthropic, OpenRouter, Ollama, or any network service.
