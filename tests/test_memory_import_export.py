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
    )
    export_path = tmp_path / "memories.json"

    exported = source.export_json(export_path)
    target = MemoryStore(tmp_path / "target")
    imported = target.import_json(export_path)

    assert exported == 1
    assert imported == 1
    assert target.search("Portable")[0].title == "Export me"
    export_data = json.loads(export_path.read_text(encoding="utf-8"))
    assert export_data["memories"][0]["tags"] == ["portable"]
