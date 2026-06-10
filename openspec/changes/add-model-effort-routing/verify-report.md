# Verify Report

## Commands

```powershell
.\.venv\Scripts\pytest.exe tests\test_model_routing.py tests\test_ui.py tests\test_agents.py tests\test_agents_cli.py tests\test_chat_client.py tests\test_chat_cli.py
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\pytest.exe
```

## Results

- Focused tests: 38 passed.
- Ruff: all checks passed.
- Full test suite: 140 passed.

## Smoke

Ran `agentos.exe` commands in a temporary project:

```powershell
agentos models effort list
agentos models effort show max
agentos models route list
agentos models route set default_chat --model local-stub --effort high
agentos chat once "routing smoke"
agentos agents start --name Router --role coding --task "Check routing" --model local-stub
```

Confirmed `chat once` used `effort=high`, routing config was written, and the
agent runtime record used `effort=high`.
