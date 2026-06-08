# Windows PowerShell Workflow

Use these commands from the repository root in Windows PowerShell.

## Validate Python

```powershell
python --version
```

AgentOS Personal requires Python 3.11 or newer. If this command is not found, install Python from `python.org` or enable the Python launcher/PATH entry in your Windows installation.

## Create And Activate A Virtual Environment

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
. .\.venv\Scripts\Activate.ps1
```

The `Set-ExecutionPolicy` command only affects the current PowerShell process. It is needed on Windows systems that block `Activate.ps1` by default.

## Install The Project For Development

```powershell
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

This installs the package in editable mode and installs the `dev` extras, including `pytest` and `ruff`.

## Validate The CLI

```powershell
agentos version
```

Expected output:

```text
AgentOS Personal 0.1.0
```

## Run Tests

```powershell
pytest
```

Expected result:

```text
16 passed
```

## Optional Ruff Check

```powershell
ruff check .
```

## Direct `.venv` Fallback Commands

If you cannot activate the virtual environment because of local PowerShell policy, use the installed executables directly:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\agentos.exe version
.\.venv\Scripts\pytest.exe
```

These commands validate the same package installation without relying on PATH activation.
