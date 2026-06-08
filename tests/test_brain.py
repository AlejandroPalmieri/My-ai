from agentos.brain.store import StrategicBrainStore


def test_ingest_markdown_creates_document_and_chunks(tmp_path):
    source = tmp_path / "strategy.md"
    source.write_text(
        "# Strategic Roadmap\n\nBuild a local planning layer.\n\nTrack decisions separately.",
        encoding="utf-8",
    )

    store = StrategicBrainStore(tmp_path)
    document = store.ingest_document(source)

    assert document.title == "Strategic Roadmap"
    assert document.path == str(source.resolve())
    assert document.content_hash
    assert (tmp_path / ".agentos" / "brain" / "index.db").exists()
    assert store.list_documents()[0].id == document.id
    assert len(store.list_chunks(document.id)) >= 1


def test_search_indexed_markdown_content(tmp_path):
    source = tmp_path / "plan.md"
    source.write_text("# Plan\n\nNeocircuit strategy uses graph-style entities.", encoding="utf-8")
    store = StrategicBrainStore(tmp_path)
    document = store.ingest_document(source)

    results = store.search("graph-style")

    assert len(results) == 1
    assert results[0].document_id == document.id
    assert results[0].title == "Plan"
    assert "graph-style entities" in results[0].chunk


def test_reingest_same_file_updates_instead_of_duplicating(tmp_path):
    source = tmp_path / "notes.txt"
    source.write_text("Alpha strategy", encoding="utf-8")
    store = StrategicBrainStore(tmp_path)
    first = store.ingest_document(source)

    source.write_text("Beta strategy", encoding="utf-8")
    second = store.ingest_document(source)

    documents = store.list_documents()
    results = store.search("Beta")

    assert first.id == second.id
    assert len(documents) == 1
    assert documents[0].content_hash == second.content_hash
    assert results[0].document_id == first.id
    assert not store.search("Alpha")


def test_like_search_fallback_when_fts_disabled(tmp_path):
    source = tmp_path / "fallback.txt"
    source.write_text("Fallback strategic retrieval", encoding="utf-8")
    store = StrategicBrainStore(tmp_path, enable_fts=False)
    store.ingest_document(source)

    results = store.search("retrieval")

    assert results[0].title == "fallback"
