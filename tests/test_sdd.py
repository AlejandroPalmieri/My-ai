import json

import pytest

from agentos.sdd.generator import (
    SDD_FILES,
    InvalidPhaseTransitionError,
    InvalidSlugError,
    advance_change,
    archive_change,
    create_change,
    get_change_status,
    list_changes,
)


def test_create_change_artifacts(tmp_path):
    change = create_change(tmp_path, "add-memory-search")

    assert change.path == tmp_path / "openspec" / "changes" / "add-memory-search"
    for filename in SDD_FILES:
        artifact = change.path / filename
        assert artifact.exists()
        assert "add-memory-search" in artifact.read_text(encoding="utf-8")

    metadata = json.loads((change.path / "metadata.json").read_text(encoding="utf-8"))
    verify_report = (change.path / "verify-report.md").read_text(encoding="utf-8")
    assert metadata["phase"] == "init"
    assert metadata["archived"] is False
    assert "## RED" in verify_report
    assert "## GREEN" in verify_report
    assert "## TRIANGULATE" in verify_report
    assert "## REFACTOR" in verify_report


def test_invalid_slug_rejected(tmp_path):
    with pytest.raises(InvalidSlugError):
        create_change(tmp_path, "Bad Slug!")


def test_phase_advancement_requires_order_unless_forced(tmp_path):
    create_change(tmp_path, "ordered-change")

    with pytest.raises(InvalidPhaseTransitionError):
        advance_change(tmp_path, "ordered-change", "design")

    explore = advance_change(tmp_path, "ordered-change", "explore")
    forced = advance_change(tmp_path, "ordered-change", "design", force=True)

    assert explore.phase == "explore"
    assert forced.phase == "design"
    assert get_change_status(tmp_path, "ordered-change").phase == "design"


def test_list_and_archive_changes(tmp_path):
    create_change(tmp_path, "archive-me")
    archived = archive_change(tmp_path, "archive-me")
    changes = list_changes(tmp_path)

    assert archived.phase == "archive"
    assert archived.archived is True
    assert changes[0].name == "archive-me"
    assert changes[0].archived is True
