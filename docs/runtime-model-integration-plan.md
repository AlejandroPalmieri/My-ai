# Runtime Model Integration Plan

This audit covers the current repository state for model/provider integration,
interactive runtime, dashboard layout, usage tracking, and agent/subagent state.
It is a planning document only; no runtime code is implemented here.

## Existing Relevant Files

- `src/agentos/cli/app.py`
  - Typer root command, subcommand registration, startup flag parsing, trace
    wrappers, and `agentos dashboard`.
  - `main()` forwards unknown no-subcommand options to the interactive CLI.
  - `--model` is not a real setting today; it is only forwarded as unknown
    text when no subcommand is specified.
- `src/agentos/cli/interactive.py`
  - Minimal local interactive loop.
  - Renders banner/dashboard, then supports only `help`, `version`, `doctor`,
    and exit commands.
  - Does not send prompts to any model provider.
- `src/agentos/ui/layout.py`
  - Pydantic dashboard data models and Rich renderers.
  - Current `RuntimeInfo` has version, profile, workspace, memory, skills,
    policies, SDD, paths, and warnings.
  - Bottom bar is static keybinding text; no active model, effort, context, or
    cost data is rendered.
- `src/agentos/ui/dashboard.py`
  - Collects local dashboard data from profile, memory, SDD, traces, policy
    files, and skills.
  - Does not collect model runtime, usage, or agent state.
- `src/agentos/ui/interactive.py`
  - Read-only/keyboard dashboard controller.
  - Supports pane focus, refresh, backup, eval, and skill scan.
  - Current pane set is `overview`, `memory`, `sdd`, `skills`, `policies`,
    `traces`, and `runtime`.
- `src/agentos/services/interfaces.py`
  - Protocols for memory, SDD, skills, policy, trace, profile, doctor, backup,
    strategic brain, and refiner.
  - No `ModelProviderService`, `RuntimeSessionService`, `UsageService`, or
    `AgentStateService` exists yet.
- `src/agentos/services/container.py`
  - Lazy local service container.
  - No runtime/model/agent service properties exist yet.
- `src/agentos/services/local.py`
  - Local-first service implementations.
  - No network model calls and no provider registry.
- `src/agentos/config/settings.py`
  - `.agentos/config.yaml` currently supports only `ui`.
  - No model provider, default model, reasoning effort, token budget, or usage
    settings exist.
- `src/agentos/config/profiles.py`
  - `.agentos/profile.yaml` supports work-mode profile fields.
  - No profile-specific model preferences exist yet.
- `src/agentos/logging/traces.py`
  - Local JSONL event schema with redaction.
  - Current event types cover commands, memory, SDD, skills, and policies.
  - No model request, model response, token usage, cost, agent spawn, or
    subagent completion event types exist.
- `tests/test_interactive_cli.py`
  - Confirms no-subcommand startup and forwarding unknown root options.
  - Does not assert model behavior.
- `tests/test_ui.py`
  - Tests theme loading, banner, dashboard data, and plain dashboard sections.
  - No runtime model/status/cost/agent assertions.
- `tests/test_dashboard_interactive.py`
  - Tests focus, refresh, local actions, and redaction behavior.
  - No agents pane or model usage tests.
- `tests/test_services.py`
  - Tests existing service container boundaries and stubs.
  - No provider/runtime/usage/agent services.
- `tests/test_cli.py`
  - Broad CLI smoke tests.
  - No `agentos models`, `agentos chat`, `agentos runtime`, or usage commands.
- `pyproject.toml`
  - Runtime dependencies are `typer`, `rich`, and `pydantic`.
  - No OpenAI SDK, Anthropic SDK, HTTP client, tokenizer, or pricing package is
    configured.

## Current Limitations

- No real AI provider integration exists.
- No provider credentials/config model exists.
- No model registry exists.
- No active runtime session object exists for the interactive CLI.
- No chat/prompt command exists.
- No streaming response handling exists.
- No token counting exists.
- No context window accounting exists.
- No accumulated token cost accounting exists.
- No reasoning/effort setting exists.
- No active model, effort, context usage, or cost appears in the bottom bar.
- No persisted usage ledger exists.
- No agent/subagent state model exists.
- No right-side dashboard pane/tab for active agents or subagents exists.
- Trace logging does not have model, usage, or agent event types.
- `.agentos/config.yaml` has only UI settings.
- `.agentos/profile.yaml` has no model defaults or runtime preferences.
- Current README mentions `agentos --model local --profile godot`, but `--model`
  is only forwarded to the local interactive loop and is not interpreted.

## Proposed Module Names And Paths

Add model/provider runtime as small, local-first modules:

- `src/agentos/models/types.py`
  - Pydantic models for providers, model IDs, requests, responses, usage, and
    pricing.
- `src/agentos/models/providers.py`
  - Provider protocols and registry.
- `src/agentos/models/local_echo.py`
  - Safe test/dry-run provider that returns deterministic local responses.
- `src/agentos/models/openai_provider.py`
  - Optional OpenAI provider adapter.
  - Must not be imported as a hard dependency unless the SDK is installed or
    added deliberately.
- `src/agentos/runtime/session.py`
  - Runtime session state, selected model, reasoning effort, context budget,
    accumulated usage, and active conversation state.
- `src/agentos/runtime/usage.py`
  - Token/cost accounting, pricing lookup, and usage ledger writing.
- `src/agentos/runtime/store.py`
  - Local persistence under `.agentos/runtime/`.
- `src/agentos/agents/state.py`
  - Active agent/subagent state models.
- `src/agentos/agents/store.py`
  - Local state store for active/completed agent runs.
- `src/agentos/agents/orchestrator.py`
  - Future local orchestration boundary.
  - Initial version should not launch autonomous subagents.

Extend existing service boundaries:

- `ModelProviderService`
- `RuntimeSessionService`
- `UsageTrackingService`
- `AgentStateService`

Local implementations:

- `LocalModelProviderService`
- `LocalRuntimeSessionService`
- `LocalUsageTrackingService`
- `LocalAgentStateService`

## Proposed Data Models

Model/provider data:

```python
class ModelProviderConfig(BaseModel):
    name: str
    provider_type: str
    default_model: str
    api_key_env: str | None = None
    base_url: str | None = None
    enabled: bool = True

class ModelSpec(BaseModel):
    provider: str
    model: str
    display_name: str
    context_window: int
    supports_streaming: bool = True
    supports_reasoning_effort: bool = False
    input_cost_per_1m: float = 0.0
    output_cost_per_1m: float = 0.0

class ModelRequest(BaseModel):
    prompt: str
    model: str | None = None
    provider: str | None = None
    reasoning_effort: str = "standard"
    max_output_tokens: int | None = None
    system_prompt: str | None = None

class ModelUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    context_window: int = 0
    context_usage_percent: float = 0.0
    cost_usd: float = 0.0

class ModelResponse(BaseModel):
    text: str
    provider: str
    model: str
    usage: ModelUsage
    finish_reason: str | None = None
```

Runtime/session data:

```python
class RuntimeStatus(BaseModel):
    session_id: str
    active_provider: str
    active_model: str
    reasoning_effort: str
    context_usage_percent: float
    accumulated_input_tokens: int
    accumulated_output_tokens: int
    accumulated_cost_usd: float
    last_updated_at: str

class RuntimeConfig(BaseModel):
    default_provider: str = "local"
    default_model: str = "local-echo"
    reasoning_effort: str = "standard"
    max_context_usage_percent: float = 90.0
    cost_warning_usd: float = 1.00
```

Agent/subagent state:

```python
class AgentRunState(BaseModel):
    id: str
    name: str
    role: str
    status: str
    parent_id: str | None = None
    provider: str | None = None
    model: str | None = None
    reasoning_effort: str | None = None
    started_at: str
    updated_at: str
    task: str
    token_usage: ModelUsage | None = None
```

Trace additions:

- `model_request_started`
- `model_response_completed`
- `model_request_failed`
- `usage_recorded`
- `agent_started`
- `agent_completed`
- `agent_failed`
- `subagent_started`
- `subagent_completed`
- `subagent_failed`

## Proposed CLI Commands

Provider/model configuration:

```powershell
agentos models list
agentos models show
agentos models set <provider>/<model>
agentos models providers
agentos models doctor
```

Runtime interaction:

```powershell
agentos chat "prompt text"
agentos chat --model openai/gpt-4.1-mini "prompt text"
agentos chat --reasoning-effort low "prompt text"
agentos runtime status
agentos runtime reset-usage
agentos runtime usage
```

Agent state:

```powershell
agentos agents list
agentos agents show <agent-id>
agentos agents clear-completed
```

Interactive CLI:

- Interpret `--model`, `--provider`, and `--reasoning-effort` in no-subcommand
  startup instead of only forwarding them as opaque text.
- Add interactive commands:
  - `model`
  - `model set <provider>/<model>`
  - `effort <low|standard|high>`
  - `usage`
  - `chat <prompt>`
  - `agents`

## Proposed UI Changes

Bottom status bar:

- Replace static-only keybinding bar with a split status/keybinding bar.
- Show:
  - active model, for example `model openai/gpt-4.1-mini`
  - reasoning effort, for example `effort standard`
  - context usage, for example `ctx 12%`
  - accumulated token cost, for example `cost $0.0031`
  - existing keybindings

Dashboard data changes:

- Add `RuntimeModelSummary` to `DashboardData`.
- Add `UsageSummary` to `DashboardData`.
- Add `AgentRunSummary` to `DashboardData`.
- Add `active_agents: list[AgentRunSummary]`.
- Add `recent_subagents: list[AgentRunSummary]`.

Right-side pane/tab:

- Current right pane is `Runtime Context`.
- Add a separate `Agents` pane in wide mode, or split the right pane into tabs:
  - `Runtime`
  - `Agents`
- In compact/plain mode, render `Active Agents` after `Runtime Context`.
- Show only metadata:
  - agent name
  - role
  - status
  - model
  - effort
  - elapsed/updated time
  - token/cost summary
- Do not render prompt content or secret-bearing payloads in the dashboard.

Interactive dashboard:

- Add `a` key for agents pane.
- Add `u` key for usage pane/detail, replacing the current placeholder meaning
  if needed.
- Add `model`, `effort`, `ctx`, and `cost` to the plain dashboard footer.

## Proposed Tests

Provider/runtime tests:

- `tests/test_model_providers.py`
  - local echo provider responds deterministically.
  - provider registry lists enabled providers.
  - missing API key reports a warning/failure without printing secret values.
- `tests/test_runtime_session.py`
  - default runtime status loads from config.
  - `set_model` updates active provider/model.
  - reasoning effort validation.
  - context usage percentage calculation.
- `tests/test_usage_tracking.py`
  - usage ledger writes valid JSONL.
  - accumulated cost calculation.
  - tests avoid wall-clock exact seconds.
  - redaction of sensitive prompt/payload data.
- `tests/test_agent_state.py`
  - active agent creation/listing.
  - subagent parent/child relationship.
  - completed agents no longer count as active.

CLI tests:

- `agentos models list` smoke test.
- `agentos models set local/local-echo` smoke test.
- `agentos runtime status` smoke test.
- `agentos chat "hello"` using local echo provider.
- `agentos --model local/local-echo --no-dashboard` applies runtime selection.

UI tests:

- Dashboard data assembly includes runtime model and usage summaries.
- Bottom bar renders active model, effort, context percent, and cost.
- Plain dashboard includes active agents.
- Interactive dashboard can focus the agents pane with `a`.
- Dashboard does not render prompt text or secret-looking values.

Trace tests:

- Model request/response events are valid JSONL.
- Usage events are emitted and redacted.
- Agent/subagent lifecycle events are emitted.

## Recommended Implementation Order

1. Add SDD change for runtime model/provider integration.
2. Extend config models with runtime settings while preserving existing
   `.agentos/config.yaml` compatibility.
3. Add local echo provider and provider/runtime/usage service interfaces.
4. Add local runtime session and usage ledger persistence.
5. Wire new services into the service container.
6. Add `agentos models list`, `agentos models set`, and `agentos runtime status`.
7. Add `agentos chat` using only the local echo provider first.
8. Extend trace event types for model, usage, and agent lifecycle events.
9. Extend dashboard data models and bottom status bar.
10. Add active agents/subagents state store and right-side dashboard pane.
11. Add optional real provider adapter after the local echo path is tested.
12. Add provider credential docs that use environment variable names only and
    never write API keys to `.agentos/config.yaml`.
13. Run full `pytest` and `ruff check .`.

## Safety Notes

- Do not store provider API keys in `.agentos/config.yaml`.
- Store only environment variable names such as `OPENAI_API_KEY`.
- Redact prompt payloads that contain sensitive terms before traces.
- Do not add autonomous shell execution as part of model integration.
- Keep local echo as the default test provider so the dashboard and CLI can be
  validated without network access.
- Add cost warning thresholds before enabling real providers by default.
