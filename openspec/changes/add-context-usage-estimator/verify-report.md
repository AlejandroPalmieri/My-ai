# Verify Report

## Commands

```powershell
.venv\Scripts\pytest.exe tests\test_context.py tests\test_ui.py tests\test_interactive_chat.py
.venv\Scripts\pytest.exe
.venv\Scripts\ruff.exe check .
.venv\Scripts\pytest.exe
```

## Results

- Focused tests: 24 passed.
- Full pytest: 146 passed.
- Ruff: all checks passed.
- Final full pytest: 146 passed.
