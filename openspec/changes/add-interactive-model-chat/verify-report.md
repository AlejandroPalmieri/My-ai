# Verify Report

## Commands

```powershell
.\.venv\Scripts\pytest.exe tests\test_interactive_chat.py tests\test_interactive_cli.py
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\pytest.exe
```

## Results

- Focused interactive tests: 10 passed.
- Ruff: all checks passed.
- Full test suite: 132 passed.

## Smoke

Ran `agentos --plain --no-dashboard --root <temp>` with stdin:

```text
/model list
Hello from interactive smoke
/usage
/clear
exit
```

Confirmed local-stub response, usage total greater than zero, and traces for
`interactive_message_sent`, `interactive_message_received`, and
`model_request_started`.

PowerShell printed the user profile execution-policy warning after pytest/smoke
runs; the commands completed successfully.
