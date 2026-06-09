from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from agentos.policies.checker import (
    APPROVAL_COMMANDS,
    DESTRUCTIVE_COMMANDS,
    SENSITIVE_PATHS,
    PolicyChecker,
)

BACKUP_INCLUDE_PATHS = [
    ".agentos/profile.yaml",
    ".agentos/skill-registry.json",
    ".agentos/memory.db",
    "policies",
    "openspec",
    ".agents/skills",
    "AGENTS.md",
]


@dataclass(frozen=True)
class Backup:
    id: str
    path: Path
    created_at: str
    file_count: int
    excluded: list[str]


@dataclass(frozen=True)
class BackupInspection:
    id: str
    path: Path
    metadata: dict[str, object]
    files: list[str]
    excluded: list[str]


@dataclass(frozen=True)
class RestoreResult:
    backup_id: str
    file_count: int


class BackupManager:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.backups_dir = self.root / ".agentos" / "backups"

    def create(self) -> Backup:
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        backup_id = _backup_id()
        created_at = datetime.now(UTC).isoformat()
        path = self.backups_dir / f"{backup_id}.zip"
        checker = self._policy_checker()
        files: list[tuple[str, Path]] = []
        excluded: list[str] = []
        for relative_path, source in self._candidate_files():
            result = checker.check_path(relative_path)
            if result.allowed:
                files.append((relative_path, source))
            else:
                excluded.append(relative_path)

        metadata = {
            "id": backup_id,
            "created_at": created_at,
            "format": "zip",
            "root": str(self.root.resolve()),
            "included_roots": BACKUP_INCLUDE_PATHS,
            "files": [relative_path for relative_path, _source in files],
            "file_count": len(files),
            "excluded": excluded,
        }
        with zipfile.ZipFile(path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("metadata.json", json.dumps(metadata, indent=2))
            for relative_path, source in files:
                archive.write(source, relative_path)
        return Backup(
            id=backup_id,
            path=path,
            created_at=created_at,
            file_count=len(files),
            excluded=excluded,
        )

    def list(self) -> list[BackupInspection]:
        if not self.backups_dir.exists():
            return []
        return sorted(
            (self.inspect(path.stem) for path in self.backups_dir.glob("*.zip")),
            key=lambda backup: str(backup.metadata.get("created_at", "")),
        )

    def inspect(self, backup_id: str) -> BackupInspection:
        path = self._backup_path(backup_id)
        with zipfile.ZipFile(path) as archive:
            metadata = json.loads(archive.read("metadata.json"))
        files = [str(item) for item in metadata.get("files", [])]
        excluded = [str(item) for item in metadata.get("excluded", [])]
        return BackupInspection(
            id=str(metadata.get("id", backup_id)),
            path=path,
            metadata=metadata,
            files=files,
            excluded=excluded,
        )

    def restore(self, backup_id: str, confirm: bool = False) -> RestoreResult:
        if not confirm:
            raise ValueError("Restore requires --confirm.")
        inspection = self.inspect(backup_id)
        root = self.root.resolve()
        with zipfile.ZipFile(inspection.path) as archive:
            for relative_path in inspection.files:
                target = (self.root / relative_path).resolve()
                if not target.is_relative_to(root):
                    raise ValueError(f"Unsafe backup path: {relative_path}")
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(relative_path) as source, target.open("wb") as destination:
                    destination.write(source.read())
        return RestoreResult(backup_id=backup_id, file_count=len(inspection.files))

    def prune(self, keep: int = 10) -> int:
        backups = self.list()
        if keep < 0:
            raise ValueError("keep must be non-negative.")
        removable = backups[: max(0, len(backups) - keep)]
        for backup in removable:
            backup.path.unlink()
        return len(removable)

    def _backup_path(self, backup_id: str) -> Path:
        path = self.backups_dir / f"{backup_id}.zip"
        if not path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_id}")
        return path

    def _candidate_files(self) -> list[tuple[str, Path]]:
        candidates: list[tuple[str, Path]] = []
        for include_path in BACKUP_INCLUDE_PATHS:
            source = self.root / include_path
            if not source.exists():
                continue
            if source.is_file():
                candidates.append((_as_posix(include_path), source))
                continue
            for child in sorted(path for path in source.rglob("*") if path.is_file()):
                relative_path = _as_posix(child.relative_to(self.root))
                candidates.append((relative_path, child))
        return candidates

    def _policy_checker(self) -> PolicyChecker:
        policies_dir = self.root / "policies"
        if policies_dir.exists():
            configured = PolicyChecker.from_directory(policies_dir)
            return PolicyChecker(
                sensitive_paths=_merge_rules(SENSITIVE_PATHS, configured.sensitive_paths),
                destructive_commands=_merge_rules(
                    DESTRUCTIVE_COMMANDS,
                    configured.destructive_commands,
                ),
                approval_commands=_merge_rules(APPROVAL_COMMANDS, configured.approval_commands),
            )
        return PolicyChecker(
            sensitive_paths=SENSITIVE_PATHS,
            destructive_commands=DESTRUCTIVE_COMMANDS,
            approval_commands=APPROVAL_COMMANDS,
        )


def _backup_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
    return f"{timestamp}-{uuid4().hex[:8]}"


def _as_posix(path: str | Path) -> str:
    return Path(path).as_posix()


def _merge_rules(defaults: list[str], configured: list[str]) -> list[str]:
    merged: list[str] = []
    for rule in [*defaults, *configured]:
        if rule not in merged:
            merged.append(rule)
    return merged
