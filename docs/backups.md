# Backups

AgentOS backups protect local configuration and metadata before larger changes.
Backups are stored as Windows-compatible `.zip` files under:

```text
.agentos/backups/
```

Commands:

```powershell
agentos backup create
agentos backup list
agentos backup inspect <backup-id>
agentos backup restore <backup-id> --confirm
agentos backup prune
```

Each backup includes a `metadata.json` file with the backup id, creation time,
format, included roots, included files, excluded files, and file count.

## Included Paths

The backup manager includes these local paths when they exist:

- `.agentos/profile.yaml`
- `.agentos/skill-registry.json`
- `.agentos/memory.db`
- `policies/`
- `openspec/`
- `.agents/skills/`
- `AGENTS.md`

## Safety

Before a file is read or added to the archive, AgentOS runs a local policy path
check against its relative path. Files that match sensitive path rules are
excluded and recorded in `metadata.json`.

Examples of excluded paths include:

- `.env`
- `*.pem`
- `*.key`
- `.ssh/`
- `credentials/`
- `secrets/`
- `token`
- `api_key`
- `banking`
- `medical_records`

Restore requires `--confirm`:

```powershell
agentos backup restore 20260608-120000-000000-abcd1234 --confirm
```

Restore overwrites files contained in the selected backup but does not delete
extra files that are not present in the archive. `backup prune` keeps the newest
10 backups by default; use `--keep` to choose a different count.
