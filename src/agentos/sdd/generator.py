from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

PHASES = (
    "init",
    "explore",
    "proposal",
    "spec",
    "design",
    "tasks",
    "apply",
    "verify",
    "sync",
    "archive",
)
SDD_FILES = (
    "proposal.md",
    "design.md",
    "tasks.md",
    "apply-progress.md",
    "verify-report.md",
    "sync-report.md",
    "metadata.json",
)
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class InvalidSlugError(ValueError):
    pass


class InvalidPhaseTransitionError(ValueError):
    pass


class SDDChange(BaseModel):
    name: str
    path: Path
    files: list[Path]
    phase: str = "init"
    archived: bool = False


class SDDMetadata(BaseModel):
    name: str
    phase: str
    archived: bool
    created_at: str
    updated_at: str
    phase_history: list[dict[str, str]]


def create_change(root: Path, change_name: str) -> SDDChange:
    _validate_slug(change_name)
    change_dir = _change_path(root, change_name)
    change_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for filename in SDD_FILES:
        path = change_dir / filename
        if filename == "metadata.json":
            if not path.exists():
                _write_metadata(path, _new_metadata(change_name))
        elif not path.exists():
            path.write_text(_template(filename, change_name), encoding="utf-8")
        files.append(path)
    metadata = _read_metadata(change_dir)
    return _change_from_metadata(change_dir, metadata, files)


def list_changes(root: Path) -> list[SDDChange]:
    changes_dir = root / "openspec" / "changes"
    if not changes_dir.exists():
        return []
    changes = []
    for change_dir in sorted(path for path in changes_dir.iterdir() if path.is_dir()):
        metadata_path = change_dir / "metadata.json"
        if not metadata_path.exists():
            continue
        metadata = _read_metadata(change_dir)
        files = [change_dir / filename for filename in SDD_FILES]
        changes.append(_change_from_metadata(change_dir, metadata, files))
    return changes


def get_change_status(root: Path, change_name: str) -> SDDChange:
    _validate_slug(change_name)
    change_dir = _change_path(root, change_name)
    metadata = _read_metadata(change_dir)
    files = [change_dir / filename for filename in SDD_FILES]
    return _change_from_metadata(change_dir, metadata, files)


def advance_change(root: Path, change_name: str, phase: str, force: bool = False) -> SDDChange:
    _validate_slug(change_name)
    if phase not in PHASES:
        raise InvalidPhaseTransitionError(f"Unknown phase: {phase}")
    change_dir = _change_path(root, change_name)
    metadata = _read_metadata(change_dir)
    if not force and not _is_next_phase(metadata.phase, phase):
        raise InvalidPhaseTransitionError(
            f"Cannot advance from {metadata.phase} to {phase} without --force."
        )
    metadata = _advance_metadata(metadata, phase)
    _write_metadata(change_dir / "metadata.json", metadata)
    files = [change_dir / filename for filename in SDD_FILES]
    return _change_from_metadata(change_dir, metadata, files)


def archive_change(root: Path, change_name: str) -> SDDChange:
    change = advance_change(root, change_name, "archive", force=True)
    metadata = _read_metadata(change.path)
    metadata.archived = True
    metadata.phase = "archive"
    metadata.updated_at = datetime.now(UTC).isoformat()
    _write_metadata(change.path / "metadata.json", metadata)
    return _change_from_metadata(change.path, metadata, change.files)


def _validate_slug(change_name: str) -> None:
    if not SLUG_PATTERN.match(change_name):
        raise InvalidSlugError(
            "Invalid change name. Use lowercase letters, numbers, and hyphens only."
        )


def _change_path(root: Path, change_name: str) -> Path:
    return root / "openspec" / "changes" / change_name


def _new_metadata(change_name: str) -> SDDMetadata:
    now = datetime.now(UTC).isoformat()
    return SDDMetadata(
        name=change_name,
        phase="init",
        archived=False,
        created_at=now,
        updated_at=now,
        phase_history=[{"phase": "init", "at": now}],
    )


def _read_metadata(change_dir: Path) -> SDDMetadata:
    path = change_dir / "metadata.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing SDD metadata: {path}")
    return SDDMetadata(**json.loads(path.read_text(encoding="utf-8")))


def _write_metadata(path: Path, metadata: SDDMetadata) -> None:
    path.write_text(json.dumps(metadata.model_dump(), indent=2) + "\n", encoding="utf-8")


def _advance_metadata(metadata: SDDMetadata, phase: str) -> SDDMetadata:
    now = datetime.now(UTC).isoformat()
    metadata.phase = phase
    metadata.updated_at = now
    metadata.archived = phase == "archive"
    metadata.phase_history.append({"phase": phase, "at": now})
    return metadata


def _is_next_phase(current: str, target: str) -> bool:
    current_index = PHASES.index(current)
    return current_index + 1 < len(PHASES) and PHASES[current_index + 1] == target


def _change_from_metadata(
    change_dir: Path,
    metadata: SDDMetadata,
    files: list[Path],
) -> SDDChange:
    return SDDChange(
        name=metadata.name,
        path=change_dir,
        files=files,
        phase=metadata.phase,
        archived=metadata.archived,
    )


def _template(filename: str, change_name: str) -> str:
    templates = {
        "proposal.md": f"""# Proposal: {change_name}

## Summary

Describe the change and why it matters.

## Scope

- In scope:
- Out of scope:

## Risks

- Risk:
""",
        "design.md": f"""# Design: {change_name}

## Architecture

Describe the module boundaries and data flow.

## Interfaces

Document public APIs, CLI commands, and file formats.

## Safety

Document guardrails and non-destructive behavior.
""",
        "tasks.md": f"""# Tasks: {change_name}

- [ ] Write failing tests.
- [ ] Implement the smallest passing change.
- [ ] Run verification.
- [ ] Update documentation.
""",
        "apply-progress.md": f"""# Apply Progress: {change_name}

## Changes Applied

- Pending.

## Open Issues

- Pending.
""",
        "verify-report.md": f"""# Verify Report: {change_name}

## RED

Record failing tests observed before implementation.

## GREEN

Record passing tests after implementation.

## TRIANGULATE

Record additional cases that prove behavior beyond one happy path.

## REFACTOR

Record cleanup performed while keeping tests green.
""",
        "sync-report.md": f"""# Sync Report: {change_name}

## Documentation

- Pending.

## Memory

- Pending.

## Repository

- Pending.
""",
    }
    return templates[filename]
