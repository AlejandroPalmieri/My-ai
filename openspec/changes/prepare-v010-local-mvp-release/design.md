# Design: prepare-v010-local-mvp-release

## Architecture

This is a release-preparation change. It does not add runtime architecture.
It documents the local MVP modules already present and verifies that local
runtime artifacts remain outside version control.

## Interfaces

- README documents user-facing CLI entrypoints.
- `CHANGELOG.md` records v0.1.0 release contents and known limitations.
- `.gitignore` excludes local secrets, `.agentos/`, local databases, traces,
  backups, and build/cache artifacts.

## Safety

- No tag is created.
- No remote push is performed.
- No local runtime data is intentionally added to version control.
- Temporary `agentos init` verification runs outside the repository tree.
