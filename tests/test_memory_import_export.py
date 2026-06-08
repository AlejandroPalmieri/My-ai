import json

from agentos.memory.store import MemoryStore


def test_memory_export_and_import_json(tmp_path):
    source = MemoryStore(tmp_path / "source")
    source.add_memory(
        project="demo",
        title="Export me",
        kind="decision",
        content="Portable technical memory",
        tags=["portable"],
        source="test-suite",
        confidence=0.9,
    )
    export_path = tmp_path / "memories.json"

    exported = source.export_json(export_path)
    target = MemoryStore(tmp_path / "target")
    imported = target.import_json(export_path)

    assert exported == 1
    assert imported == 1
    imported_memory = target.search("Portable")[0]
    assert imported_memory.title == "Export me"
    assert imported_memory.source == "test-suite"
    assert imported_memory.confidence == 0.9
    export_data = json.loads(export_path.read_text(encoding="utf-8"))
    assert export_data["memories"][0]["tags"] == ["portable"]
