# Design: add-doctor-command

## Architecture

`src/agentos/diagnostics/doctor.py` owns diagnostic models and check logic. It returns a `DoctorReport` containing ordered `DoctorCheck` rows with `pass`, `warn`, or `fail` status.

`LocalDoctorService` wraps the diagnostics module so the CLI continues to call local service adapters rather than embedding diagnostic logic directly in command handlers.

`agentos doctor` starts a local trace, runs the service, renders a Rich table, records whether the report is healthy, and exits with code 1 only when a check reports `fail`.

## Interfaces

- Public API: `run_doctor(root: Path, agentos_executable: Path | None = None, shim_path: Path | None = None, path_env: str | None = None) -> DoctorReport`.
- CLI: `agentos doctor [--root PATH]`.
- Output: Rich table with columns `Check`, `Status`, and `Detail`.
- Critical failures: missing project root, missing local `agentos.exe`, or SQLite failure.
- Warnings: missing `pyproject.toml`, missing policy files, missing/unwired Windows shim, or unavailable SQLite FTS5.

## Safety

The command is read-only. It probes SQLite using an in-memory database, checks existence of known project files, and reads only the Windows `agentos.cmd` shim when present. It does not read `.env`, credentials, private keys, secrets directories, medical records, banking files, or arbitrary user files. It does not modify PATH, install packages, repair files, delete data, or execute destructive commands.
