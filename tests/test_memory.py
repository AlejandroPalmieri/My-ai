import sqlite3

from agentos.memory.store import MemoryStore


def test_add_and_search_memory(tmp_path):
    store = MemoryStore(tmp_path)

    memory = store.add_memory(
        project="demo",
        title="SQLite foundation",
        kind="decision",
        content="Use SQLite as the local technical memory.",
        tags=["sqlite", "memory"],
        source="architecture",
        confidence=0.85,
    )

    results = store.search("SQLite", project="demo")

    assert isinstance(memory.id, str)
    assert (tmp_path / ".agentos" / "memory.db").exists()
    assert len(results) == 1
    assert results[0].title == "SQLite foundation"
    assert results[0].tags == ["sqlite", "memory"]
    assert results[0].source == "architecture"
    assert results[0].confidence == 0.85


def test_initialization_creates_schema_version_and_text_primary_key(tmp_path):
    store = MemoryStore(tmp_path)

    with sqlite3.connect(store.db_path) as connection:
        memory_columns = {
            row[1]: row[2] for row in connection.execute("PRAGMA table_info(memories)")
        }
        schema_version = connection.execute(
            "SELECT version FROM schema_version WHERE id = 'memory'"
        ).fetchone()

    assert memory_columns["id"] == "TEXT"
    assert memory_columns["source"] == "TEXT"
    assert memory_columns["confidence"] == "REAL"
    assert schema_version == (1,)


def test_search_filters_by_project(tmp_path):
    store = MemoryStore(tmp_path)
    store.add_memory("alpha", "Alpha note", "note", "shared keyword", [])
    store.add_memory("beta", "Beta note", "note", "shared keyword", [])

    results = store.search("shared", project="beta")

    assert [item.project for item in results] == ["beta"]


def test_search_includes_project_kind_and_tags(tmp_path):
    store = MemoryStore(tmp_path)
    store.add_memory("engram", "Search fields", "architecture", "Body text", ["indexed-tag"])

    assert store.search("engram")[0].project == "engram"
    assert store.search("architecture")[0].kind == "architecture"
    assert store.search("indexed-tag")[0].tags == ["indexed-tag"]


def test_like_search_fallback_when_fts_disabled(tmp_path):
    store = MemoryStore(tmp_path, enable_fts=False)
    store.add_memory("demo", "Fallback title", "note", "Needle content", ["fallback"])

    results = store.search("Needle")

    assert len(results) == 1
    assert results[0].title == "Fallback title"


def test_list_get_and_delete_memory(tmp_path):
    store = MemoryStore(tmp_path)
    first = store.add_memory("demo", "First", "note", "First content", [])
    second = store.add_memory("demo", "Second", "note", "Second content", [])

    listed = store.list_memories(project="demo")
    fetched = store.get_memory(first.id)
    deleted = store.delete_memory(first.id)

    assert [item.id for item in listed] == [first.id, second.id]
    assert fetched.title == "First"
    assert deleted is True
    assert store.get_memory(first.id) is None
