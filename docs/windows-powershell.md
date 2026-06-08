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

Run the local diagnostic command when setup or PATH behavior looks wrong:

```powershell
agentos doctor
```

The doctor command checks Python, the project root, `.venv\Scripts\agentos.exe`, SQLite, SQLite FTS5, policy files, and the Windows `agentos.cmd` shim.

## Install The Persistent `agentos` Command

After the project is installed, run this once from the repository root:

```powershell
.\scripts\install-agentos-command.ps1
```

This writes an `agentos.cmd` shim to your user `WindowsApps` directory, which is normally already on PATH. The shim points at this repository's `.venv\Scripts\agentos.exe`. Open a new PowerShell terminal and validate it:

```powershell
agentos version
```

Normal source changes are reflected because the package is installed in editable mode. Re-run the installer after dependency, virtual environment, or CLI entrypoint changes:

```powershell
.\scripts\install-agentos-command.ps1
```

## Run Tests

```powershell
pytest
```

Expected result:

```text
36 passed
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
