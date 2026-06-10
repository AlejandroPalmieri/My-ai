# Design

`src/agentos/models/client.py` coordinates model profile selection, provider
lookup, tracing, and usage recording.

Provider implementations live under `src/agentos/models/providers/`:

- `base.py`: protocol-like base models and provider interface.
- `local_stub.py`: deterministic offline response.
- `openai_compatible.py`: lazy `httpx` adapter for `/chat/completions`.

The CLI exposes `agentos chat once` and `agentos chat status`. Only explicit
message and system prompt strings are sent to providers. Local files, memory,
traces, and secrets are never included automatically.

Usage is written to both the active model state in `.agentos/models.yaml` and
the usage store `.agentos/model-usage.json`.
