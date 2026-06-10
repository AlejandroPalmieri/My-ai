# Verify Report

## Commands

```powershell
.\.venv\Scripts\pytest.exe tests\test_ui.py
.\.venv\Scripts\pytest.exe
.\.venv\Scripts\ruff.exe check .
```

## Result

- UI tests: 8 passed.
- Full test suite: 112 passed.
- Ruff: all checks passed.

PowerShell printed the user profile execution-policy warning after test runs;
the test commands themselves completed successfully.
