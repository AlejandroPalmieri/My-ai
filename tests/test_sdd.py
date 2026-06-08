from agentos.sdd.generator import SDD_FILES, create_change


def test_create_change_artifacts(tmp_path):
    change = create_change(tmp_path, "add-memory-search")

    assert change.path == tmp_path / "openspec" / "changes" / "add-memory-search"
    for filename in SDD_FILES:
        artifact = change.path / filename
        assert artifact.exists()
        assert "add-memory-search" in artifact.read_text(encoding="utf-8")
