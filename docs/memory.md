# Technical Memory

AgentOS technical memory is a local SQLite store for project notes, decisions,
implementation facts, and retrieval-friendly operational context.

Storage:

```text
.agentos/memory.db
```

Commands:

```powershell
agentos memory add --project demo --title "Decision" --kind decision --content "Use SQLite for local memory."
agentos memory search SQLite --project demo
agentos memory list
agentos memory get <memory-id>
agentos memory delete <memory-id>
agentos memory export --format json --output memories.json
agentos memory import memories.json
```

`memory add` uses the active profile's `memory_project` when `--project` is
omitted. Profiles are configured in `.agentos/profile.yaml`.

## Schema

Each memory stores:

- `id`
- `project`
- `title`
- `kind`
- `content`
- `tags`
- `source`
- `confidence`
- `created_at`
- `updated_at`

Search uses SQLite FTS5 when available and falls back to `LIKE` queries on
systems without FTS5.

## Safety

Memory is local-first. AgentOS does not send memories to external services and
does not read secrets automatically. Keep secrets, API keys, SSH keys, medical
records, banking data, and credential files out of memory content.

The database is runtime data and should not be committed. `.gitignore` excludes
`.agentos/` and local database file patterns.
