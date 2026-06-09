# Proposal: add-local-backup-rollback

## Summary

Add local backup and rollback support for critical AgentOS configuration and
metadata. This protects profiles, policy files, memory metadata, SDD artifacts,
skills, and local instructions before larger changes.

## Scope

- In scope:
- Zip backups under `.agentos/backups/`.
- Backup metadata embedded as `metadata.json`.
- CLI commands for create, list, inspect, restore, and prune.
- Policy checks before files are read or added to a backup.
- Restore gated by `--confirm`.
- Default pruning that keeps the newest 10 backups.
- Out of scope:
- Remote backup targets.
- Encrypted backup storage.
- Automatic restore or backup scheduling.

## Risks

- Risk: Sensitive files inside included directories could be archived.
  Mitigation: Check every candidate relative path with local policy rules before reading it.
- Risk: Restore overwrites local metadata.
  Mitigation: Require explicit `--confirm` and restore only selected archive members.
- Risk: Backup pruning deletes older backups.
  Mitigation: Keep the newest 10 by default and expose `--keep`.
