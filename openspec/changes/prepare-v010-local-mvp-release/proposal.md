# Proposal: prepare-v010-local-mvp-release

## Summary

Prepare AgentOS Personal for the v0.1.0 local MVP release by completing release
documentation, hardening ignore rules, adding a changelog, and verifying the
CLI in a temporary project.

## Scope

- In scope:
- README release sections: overview, Windows installation, quickstart, commands,
  safety notes, and roadmap pointer.
- Required documentation audit.
- `docs/memory.md`.
- `CHANGELOG.md`.
- `.gitignore` safety hardening for secrets, local databases, traces, and backups.
- Version verification for `0.1.0`.
- Full test and lint verification.
- Out of scope:
- Git tag creation.
- Remote push.
- Packaging upload.

## Risks

- Risk: local runtime databases or backups could be included in the release.
  Mitigation: audit `git status`, `git ls-files`, and strengthen `.gitignore`.
- Risk: release docs could overstate implemented capabilities.
  Mitigation: keep known limitations explicit.
