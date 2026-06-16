# Security

AgentOS Personal uses a local-first policy checker for sensitive paths and dangerous command strings. The checker analyzes text only. It does not execute commands, read secret files, or repair policy violations automatically.

## Policy Files

Policy files live under `policies/`:

- `sensitive_paths.yaml`: path patterns that must be blocked before access.
- `destructive_commands.yaml`: command patterns that must be blocked before execution.
- `approval_rules.yaml`: command patterns that should return a warning and require explicit review.

The supported YAML format is intentionally small: one top-level key with a list of string values.

## Severity

- `allow`: no local policy matched.
- `warn`: an approval rule matched; the operation is not blocked, but it requires explicit user review.
- `block`: a sensitive path or destructive command matched.

Every result includes a reason, the matched rule when one exists, and the rule type.

## Examples

Blocked sensitive paths:

```text
.env
config/prod.pem
C:\Users\name\.ssh\id_ed25519
credentials/service-token.txt
notes/medical_records/visit.md
banking/export.csv
```

Blocked destructive commands:

```text
rm -rf project
del /s /q build
Remove-Item -Path .\build -Recurse -Force
git push --force origin main
git reset --hard HEAD
DROP DATABASE production
docker system prune -af
format C:
diskpart /s wipe.txt
```

Warning examples:

```text
git push origin main
pip install package-name
docker run image-name
```

Allowed example:

```text
pytest
```

## CLI

```powershell
agentos policies check --path .env
agentos policies check --command "Remove-Item -Path .\build -Recurse -Force"
agentos policies list
agentos policies explain
```

`policies check` exits with code 1 for `block` results and code 0 for `allow` or `warn` results. This keeps warning rules visible without treating them as hard failures.

## Retrieval Safety

Chat retrieval is explicit opt-in only. AgentOS does not send technical memory,
Strategic Brain chunks, files, traces, backups, or local data unless the user
uses retrieval flags or session commands.

Safe retrieval behavior:

- `--with-memory` and `/memory on` opt in technical memory excerpts.
- `--with-brain` and `/brain on` opt in Strategic Brain excerpts.
- `--dry-run-context` shows what would be sent without calling a provider.
- Trace payloads include counts and ids, not full context bodies.
- Hidden paths and sensitive-looking content are filtered from retrieval output.
