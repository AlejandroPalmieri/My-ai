# Design: add-local-backup-rollback

## Architecture

- `src/agentos/backups/manager.py` owns zip creation, inspection, restore, and prune.
- `BackupService` exposes the behavior through the service container.
- CLI handlers in `src/agentos/cli/app.py` stay thin and call `ServiceContainer.backups`.
- Backup archives live under `.agentos/backups/` and contain a root `metadata.json`.

## Interfaces

- API:
  - `BackupManager(root).create()`
  - `BackupManager(root).list()`
  - `BackupManager(root).inspect(backup_id)`
  - `BackupManager(root).restore(backup_id, confirm=True)`
  - `BackupManager(root).prune(keep=10)`
- CLI:
  - `agentos backup create`
  - `agentos backup list`
  - `agentos backup inspect <backup-id>`
  - `agentos backup restore <backup-id> --confirm`
  - `agentos backup prune`
- Format: Windows-compatible zip with `metadata.json` and included files stored by relative path.

## Safety

- Candidate files are checked with policy path rules before they are read.
- Sensitive candidate files are excluded and recorded in metadata.
- Restore rejects calls without `--confirm`.
- Restore validates archive member paths before writing.
- Restore does not delete files that are not present in the archive.
