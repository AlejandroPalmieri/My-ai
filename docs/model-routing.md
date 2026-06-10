# Model Effort And Routing

AgentOS defines local effort profiles and route defaults for model-aware
workflows. Routing is local metadata only; it does not call providers or read
API keys.

## Effort Levels

- `low`: fast, cheap, simple tasks.
- `medium`: normal planning and chat.
- `high`: architecture, code review, multi-step reasoning, and coding tasks.
- `max`: difficult design, debugging, safety review, and final verification.

Inspect them with:

```powershell
agentos models effort list
agentos models effort show high
```

Each effort profile includes:

- label
- description
- default temperature
- default max output token hint
- reasoning budget hint
- intended use

## Routing Config

Routing rules live in:

```text
.agentos/model-routing.yaml
```

Default routes:

```yaml
routes:
  default_chat:
    model_profile: null
    effort: medium
  coding:
    model_profile: null
    effort: high
  sdd_explore:
    model_profile: null
    effort: medium
  sdd_design:
    model_profile: null
    effort: high
  sdd_verify:
    model_profile: null
    effort: max
  refiner_analyze:
    model_profile: null
    effort: high
  safety_review:
    model_profile: null
    effort: max
```

`model_profile: null` means "use the active model profile".

## Commands

```powershell
agentos models route list
agentos models route set default_chat --model local-stub --effort medium
agentos models route set coding --model openrouter-auto --effort high
agentos models route set safety_review --model openai-gpt-5-5-thinking --effort max
```

Explicit command-line effort still wins:

```powershell
agentos chat once "Summarize this" --effort low
```

If no `--effort` is supplied, `agentos chat once` uses the `default_chat`
route. `agentos agents start` uses the `coding` route when `--effort` is
omitted.
