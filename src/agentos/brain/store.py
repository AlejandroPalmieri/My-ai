from __future__ import annotations

import hashlib
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

from agentos.policies.checker import PolicyChecker, create_default_policies

SUPPORTED_EXTENSIONS = {".md", ".txt"}
BRAIN_SCHEMA_VERSION = 1
CHUNK_TARGET_CHARS = 1200


class BrainDocument(BaseModel):
    id: str
    path: str
    title: str
    content_hash: str
    created_at: str
    updated_at: str


class BrainChunk(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    content: str
    created_at: str


class BrainSearchResult(BaseModel):
    document_id: str
    chunk_id: str
    title: str
    path: str
    chunk: str
    chunk_index: int


class StrategicBrainStore:
    def __init__(self, root: Path, enable_fts: bool = True) -> None:
        self.root = root
        self.brain_dir = root / ".agentos" / "brain"
        self.db_path = self.brain_dir / "index.db"
        self.brain_dir.mkdir(parents=True, exist_ok=True)
        self._fts_enabled = enable_fts
        self._fts_available = False
        self._ensure_schema()

    def ingest_document(self, path: Path) -> BrainDocument:
        source = path.resolve()
        _validate_supported_path(source)
        self._ensure_path_allowed(source)
        content = source.read_text(encoding="utf-8")
        title = _title_from_content(source, content)
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        now = datetime.now(UTC).isoformat()
        chunks = _split_chunks(content)

        with self._connect() as connection:
            existing = connection.execute(
                "SELECT * FROM documents WHERE path = ?",
                (str(source),),
            ).fetchone()
            document_id = existing["id"] if existing else uuid4().hex
            created_at = existing["created_at"] if existing else now
            connection.execute(
                """
                INSERT INTO documents (id, path, title, content_hash, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    title = excluded.title,
                    content_hash = excluded.content_hash,
                    updated_at = excluded.updated_at
                """,
                (document_id, str(source), title, content_hash, created_at, now),
            )
            self._replace_chunks(connection, document_id, chunks, now)
            row = connection.execute(
                "SELECT * FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()
        return _document_from_row(row)

    def search(self, query: str, limit: int = 20) -> list[BrainSearchResult]:
        with self._connect() as connection:
            if self._has_fts(connection):
                rows = self._search_fts(connection, query, limit)
            else:
                rows = self._search_like(connection, query, limit)
        return [_search_result_from_row(row) for row in rows]

    def list_documents(self) -> list[BrainDocument]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM documents ORDER BY updated_at DESC",
            ).fetchall()
        return [_document_from_row(row) for row in rows]

    def get_document(self, document_id: str) -> BrainDocument | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()
        return None if row is None else _document_from_row(row)

    def list_chunks(self, document_id: str) -> list[BrainChunk]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM chunks WHERE document_id = ? ORDER BY chunk_index ASC",
                (document_id,),
            ).fetchall()
        return [_chunk_from_row(row) for row in rows]

    def _ensure_path_allowed(self, source: Path) -> None:
        create_default_policies(self.root)
        result = PolicyChecker.from_directory(self.root / "policies").check_path(str(source))
        if not result.allowed:
            raise PermissionError(f"Brain ingest blocked by policy: {result.reason}")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    id TEXT PRIMARY KEY,
                    version INTEGER NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    path TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS links (
                    id TEXT PRIMARY KEY,
                    source_document_id TEXT NOT NULL,
                    target TEXT NOT NULL,
                    label TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(source_document_id) REFERENCES documents(id)
                )
                """
            )
            connection.execute(
                """
                INSERT INTO schema_version (id, version, updated_at)
                VALUES ('brain', ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    version = excluded.version,
                    updated_at = excluded.updated_at
                """,
                (BRAIN_SCHEMA_VERSION, datetime.now(UTC).isoformat()),
            )
            self._ensure_fts(connection)

    def _ensure_fts(self, connection: sqlite3.Connection) -> None:
        if not self._fts_enabled:
            self._fts_available = False
            return
        try:
            connection.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
                USING fts5(chunk_id UNINDEXED, document_id UNINDEXED, path, title, content)
                """
            )
            self._fts_available = True
            self._rebuild_fts(connection)
        except sqlite3.OperationalError:
            self._fts_available = False

    def _has_fts(self, connection: sqlite3.Connection) -> bool:
        if not self._fts_enabled or not self._fts_available:
            return False
        try:
            connection.execute("SELECT rowid FROM chunks_fts LIMIT 1").fetchall()
            return True
        except sqlite3.OperationalError:
            self._fts_available = False
            return False

    def _replace_chunks(
        self,
        connection: sqlite3.Connection,
        document_id: str,
        chunks: list[str],
        now: str,
    ) -> None:
        connection.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
        if self._has_fts(connection):
            connection.execute("DELETE FROM chunks_fts WHERE document_id = ?", (document_id,))
        document = connection.execute(
            "SELECT * FROM documents WHERE id = ?",
            (document_id,),
        ).fetchone()
        for index, chunk in enumerate(chunks):
            chunk_id = uuid4().hex
            connection.execute(
                """
                INSERT INTO chunks (id, document_id, chunk_index, content, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (chunk_id, document_id, index, chunk, now),
            )
            if self._has_fts(connection):
                connection.execute(
                    """
                    INSERT INTO chunks_fts (chunk_id, document_id, path, title, content)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (chunk_id, document_id, document["path"], document["title"], chunk),
                )

    def _rebuild_fts(self, connection: sqlite3.Connection) -> None:
        if not self._fts_enabled or not self._fts_available:
            return
        connection.execute("DELETE FROM chunks_fts")
        rows = connection.execute(
            """
            SELECT c.id AS chunk_id, c.document_id, d.path, d.title, c.content
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            """
        ).fetchall()
        for row in rows:
            connection.execute(
                """
                INSERT INTO chunks_fts (chunk_id, document_id, path, title, content)
                VALUES (?, ?, ?, ?, ?)
                """,
                (row["chunk_id"], row["document_id"], row["path"], row["title"], row["content"]),
            )

    def _search_fts(
        self,
        connection: sqlite3.Connection,
        query: str,
        limit: int,
    ) -> list[sqlite3.Row]:
        sql = """
            SELECT d.id AS document_id, c.id AS chunk_id, d.title, d.path,
                   c.content AS chunk, c.chunk_index
            FROM chunks_fts f
            JOIN chunks c ON c.id = f.chunk_id
            JOIN documents d ON d.id = c.document_id
            WHERE chunks_fts MATCH ?
            ORDER BY d.updated_at DESC, c.chunk_index ASC
            LIMIT ?
        """
        try:
            return list(connection.execute(sql, (_quote_fts_query(query), limit)).fetchall())
        except sqlite3.OperationalError:
            return self._search_like(connection, query, limit)

    def _search_like(
        self,
        connection: sqlite3.Connection,
        query: str,
        limit: int,
    ) -> list[sqlite3.Row]:
        pattern = f"%{query}%"
        sql = """
            SELECT d.id AS document_id, c.id AS chunk_id, d.title, d.path,
                   c.content AS chunk, c.chunk_index
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE d.title LIKE ? OR d.path LIKE ? OR c.content LIKE ?
            ORDER BY d.updated_at DESC, c.chunk_index ASC
            LIMIT ?
        """
        return list(connection.execute(sql, (pattern, pattern, pattern, limit)).fetchall())


def _validate_supported_path(source: Path) -> None:
    if source.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("Strategic brain ingest supports .md and .txt files only.")
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(f"Document not found: {source}")


def _title_from_content(source: Path, content: str) -> str:
    if source.suffix.lower() == ".md":
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip() or source.stem
    return source.stem


def _split_chunks(content: str) -> list[str]:
    paragraphs = [part.strip() for part in content.replace("\r\n", "\n").split("\n\n")]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if not paragraph:
            continue
        if current and len(current) + len(paragraph) + 2 > CHUNK_TARGET_CHARS:
            chunks.append(current)
            current = paragraph
        else:
            current = paragraph if not current else f"{current}\n\n{paragraph}"
    if current:
        chunks.append(current)
    return chunks or [content.strip()]


def _quote_fts_query(query: str) -> str:
    escaped = query.replace('"', '""')
    return f'"{escaped}"'


def _document_from_row(row: sqlite3.Row) -> BrainDocument:
    return BrainDocument(
        id=row["id"],
        path=row["path"],
        title=row["title"],
        content_hash=row["content_hash"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _chunk_from_row(row: sqlite3.Row) -> BrainChunk:
    return BrainChunk(
        id=row["id"],
        document_id=row["document_id"],
        chunk_index=int(row["chunk_index"]),
        content=row["content"],
        created_at=row["created_at"],
    )


def _search_result_from_row(row: sqlite3.Row) -> BrainSearchResult:
    return BrainSearchResult(
        document_id=row["document_id"],
        chunk_id=row["chunk_id"],
        title=row["title"],
        path=row["path"],
        chunk=row["chunk"],
        chunk_index=int(row["chunk_index"]),
    )
