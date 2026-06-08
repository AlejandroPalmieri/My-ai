from agentos.memory.store import MemoryStore


def test_add_and_search_memory(tmp_path):
    store = MemoryStore(tmp_path)

    memory = store.add_memory(
        project="demo",
        title="SQLite foundation",
        kind="decision",
        content="Use SQLite as the local technical memory.",
        tags=["sqlite", "memory"],
    )

    results = store.search("SQLite", project="demo")

    assert memory.id > 0
    assert (tmp_path / ".agentos" / "memory.db").exists()
    assert len(results) == 1
    assert results[0].title == "SQLite foundation"
    assert results[0].tags == ["sqlite", "memory"]


def test_search_filters_by_project(tmp_path):
    store = MemoryStore(tmp_path)
    store.add_memory("alpha", "Alpha note", "note", "shared keyword", [])
    store.add_memory("beta", "Beta note", "note", "shared keyword", [])

    results = store.search("shared", project="beta")

    assert [item.project for item in results] == ["beta"]
