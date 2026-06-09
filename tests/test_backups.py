import json
import zipfile

import pytest

from agentos.backups.manager import BackupManager


def test_backup_create_writes_zip_with_metadata_and_expected_files(tmp_path):
    _seed_backup_source(tmp_path)

    backup = BackupManager(tmp_path).create()

    assert backup.path.exists()
    assert backup.path.suffix == ".zip"
    with zipfile.ZipFile(backup.path) as archive:
        names = set(archive.namelist())
        metadata = json.loads(archive.read("metadata.json"))

    assert "metadata.json" in names
    assert ".agentos/profile.yaml" in names
    assert ".agentos/skill-registry.json" in names
    assert ".agentos/memory.db" in names
    assert "policies/sensitive_paths.yaml" in names
    assert "openspec/changes/demo/proposal.md" in names
    assert ".agents/skills/demo/SKILL.md" in names
    assert "AGENTS.md" in names
    assert metadata["id"] == backup.id
    assert metadata["format"] == "zip"
    assert metadata["file_count"] == len(metadata["files"])


def test_backup_inspect_returns_metadata_without_extracting(tmp_path):
    _seed_backup_source(tmp_path)
    backup = BackupManager(tmp_path).create()

    inspected = BackupManager(tmp_path).inspect(backup.id)

    assert inspected.id == backup.id
    assert inspected.path == backup.path
    assert ".agentos/profile.yaml" in inspected.files
    assert inspected.metadata["file_count"] == len(inspected.files)


def test_backup_restore_requires_confirm_and_restores_files(tmp_path):
    _seed_backup_source(tmp_path)
    manager = BackupManager(tmp_path)
    backup = manager.create()
    profile = tmp_path / ".agentos" / "profile.yaml"
    profile.write_text("name: changed\n", encoding="utf-8")

    with pytest.raises(ValueError, match="--confirm"):
        manager.restore(backup.id, confirm=False)

    restored = manager.restore(backup.id, confirm=True)

    assert restored.file_count > 0
    assert profile.read_text(encoding="utf-8") == "name: default\n"


def test_backup_excludes_sensitive_files_by_policy(tmp_path):
    _seed_backup_source(tmp_path)
    (tmp_path / ".agents" / "skills" / "demo" / ".env").write_text(
        "TOKEN=secret",
        encoding="utf-8",
    )
    (tmp_path / "openspec" / "changes" / "demo" / "private.pem").write_text(
        "secret",
        encoding="utf-8",
    )

    backup = BackupManager(tmp_path).create()

    with zipfile.ZipFile(backup.path) as archive:
        names = set(archive.namelist())
        metadata = json.loads(archive.read("metadata.json"))

    assert ".agents/skills/demo/.env" not in names
    assert "openspec/changes/demo/private.pem" not in names
    assert ".agents/skills/demo/.env" in metadata["excluded"]
    assert "openspec/changes/demo/private.pem" in metadata["excluded"]


def test_backup_prune_keeps_last_ten_by_default(tmp_path):
    _seed_backup_source(tmp_path)
    manager = BackupManager(tmp_path)
    for _ in range(12):
        manager.create()

    removed = manager.prune()

    assert removed == 2
    assert len(manager.list()) == 10


def _seed_backup_source(root):
    (root / ".agentos").mkdir(parents=True)
    (root / ".agentos" / "profile.yaml").write_text("name: default\n", encoding="utf-8")
    (root / ".agentos" / "skill-registry.json").write_text("{}", encoding="utf-8")
    (root / ".agentos" / "memory.db").write_text("sqlite", encoding="utf-8")
    (root / "policies").mkdir()
    (root / "policies" / "sensitive_paths.yaml").write_text(
        "sensitive_paths:\n  - .env\n  - '*.pem'\n",
        encoding="utf-8",
    )
    (root / "policies" / "destructive_commands.yaml").write_text(
        "destructive_commands:\n  - rm -rf\n",
        encoding="utf-8",
    )
    (root / "policies" / "approval_rules.yaml").write_text(
        "approval_commands:\n  - git push\n",
        encoding="utf-8",
    )
    (root / "openspec" / "changes" / "demo").mkdir(parents=True)
    (root / "openspec" / "changes" / "demo" / "proposal.md").write_text(
        "# Demo\n",
        encoding="utf-8",
    )
    (root / ".agents" / "skills" / "demo").mkdir(parents=True)
    (root / ".agents" / "skills" / "demo" / "SKILL.md").write_text(
        "---\nname: demo\ndescription: Demo.\n---\n",
        encoding="utf-8",
    )
    (root / "AGENTS.md").write_text("# Instructions\n", encoding="utf-8")
