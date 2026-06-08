from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

MEMORY_SCHEMA_VERSION = 1


class Memory(BaseModel):
    id: str
    project: str
    title: str
    kind: str
    content: str
    tags: list[str]
    source: str | None = None
    confidence: float = 1.0
    created_at: str
    updated_at: str


class MemoryStore:
    def __init__(self, root: Path, enable_fts: bool = True) -> None:
        self.root = root
        self.agentos_dir = root / ".agentos"
        self.db_path = self.agentos_dir / "memory.db"
        self.agentos_dir.mkdir(parents=True, exist_ok=True)
        self._fts_enabled = enable_fts
        self._fts_available = False
        self._ensure_schema()

    def add_memory(
        self,
        project: str,
        title: str,
        kind: str,
        content: str,
        tags: list[str],
        source: str | None = None,
        confidence: float = 1.0,
        memory_id: str | None = None,
        created_at: str | None = None,
        updated_at: str | None = None,
    ) -> Memory:
        now = datetime.now(UTC).isoformat()
        memory = Memory(
            id=memory_id or uuid4().hex,
            project=project,
            title=title,
            kind=kind,
            content=content,
            tags=tags,
            source=source,
            confidence=confidence,
            created_at=created_at or now,
            updated_at=updated_at or now,
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO memories (
                    id, project, title, kind, content, tags, source, confidence,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    project = excluded.project,
                    title = excluded.title,
                    kind = excluded.kind,
                    content = excluded.content,
                    tags = excluded.tags,
                    source = excluded.source,
                    confidence = excluded.confidence,
                    updated_at = excluded.updated_at
                """,
                (
                    memory.id,
                    memory.project,
                    memory.title,
                    memory.kind,
                    memory.content,
                    json.dumps(memory.tags),
                    memory.source,
                    memory.confidence,
                    memory.created_at,
                    memory.updated_at,
                ),
            )
            self._index_memory(connection, memory)
        return memory

    def search(self, query: str, project: str | None = None, limit: int = 20) -> list[Memory]:
        with self._connect() as connection:
            if self._has_fts(connection):
                rows = self._search_fts(connection, query, project, limit)
            else:
                rows = self._search_like(connection, query, project, limit)
        return [self._row_to_memory(row) for row in rows]

    def list_memories(
        self,
        project: str | None = None,
        kind: str | None = None,
        limit: int | None = None,
    ) -> list[Memory]:
        sql = "SELECT * FROM memories"
        params: list[object] = []
        filters = []
        if project is not None:
            filters.append("project = ?")
            params.append(project)
        if kind is not None:
            filters.append("kind = ?")
            params.append(kind)
        if filters:
            sql += " WHERE " + " AND ".join(filters)
        sql += " ORDER BY created_at ASC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [self._row_to_memory(row) for row in rows]

    def get_memory(self, memory_id: str) -> Memory | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_memory(row)

    def delete_memory(self, memory_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            if self._has_fts(connection):
                try:
                    connection.execute("DELETE FROM memories_fts WHERE memory_id = ?", (memory_id,))
                except sqlite3.OperationalError:
                    self._rebuild_fts(connection)
        return cursor.rowcount > 0

    def export_json(self, path: Path) -> int:
        memories = self.list_memories()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_memories_to_json(memories) + "\n", encoding="utf-8")
        return len(memories)

    def export_json_text(self) -> str:
        return _memories_to_json(self.list_memories())

    def import_json(self, path: Path) -> int:
        data = json.loads(path.read_text(encoding="utf-8"))
        count = 0
        for item in data.get("memories", []):
            self.add_memory(
                project=item["project"],
                title=item["title"],
                kind=item["kind"],
                content=item["content"],
                tags=list(item.get("tags") or []),
                source=item.get("source"),
                confidence=float(item.get("confidence", 1.0)),
                memory_id=item.get("id"),
                created_at=item.get("created_at"),
                updated_at=item.get("updated_at"),
            )
            count += 1
        return count

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            self._migrate_legacy_memories(connection)
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
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    project TEXT NOT NULL,
                    title TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT,
                    source TEXT,
                    confidence REAL DEFAULT 1.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                INSERT INTO schema_version (id, version, updated_at)
                VALUES ('memory', ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    version = excluded.version,
                    updated_at = excluded.updated_at
                """,
                (MEMORY_SCHEMA_VERSION, datetime.now(UTC).isoformat()),
            )
            self._ensure_fts(connection)

    def _migrate_legacy_memories(self, connection: sqlite3.Connection) -> None:
        if not _table_exists(connection, "memories"):
            return
        columns = {row["name"]: row for row in connection.execute("PRAGMA table_info(memories)")}
        id_type = columns["id"]["type"].upper() if "id" in columns else ""
        if id_type == "TEXT" and "source" in columns:
            return

        legacy_rows = list(connection.execute("SELECT * FROM memories").fetchall())
        connection.execute("DROP TABLE IF EXISTS memories_fts")
        connection.execute("ALTER TABLE memories RENAME TO memories_legacy")
        connection.execute(
            """
            CREATE TABLE memories (
                id TEXT PRIMARY KEY,
                project TEXT NOT NULL,
                title TEXT NOT NULL,
                kind TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT,
                source TEXT,
                confidence REAL DEFAULT 1.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        for row in legacy_rows:
            connection.execute(
                """
                INSERT INTO memories (
                    id, project, title, kind, content, tags, source, confidence,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(row["id"]),
                    row["project"],
                    row["title"],
                    row["kind"],
                    row["content"],
                    row["tags"],
                    None,
                    1.0,
                    row["created_at"],
                    row["updated_at"],
                ),
            )
        connection.execute("DROP TABLE memories_legacy")

    def _ensure_fts(self, connection: sqlite3.Connection) -> None:
        if not self._fts_enabled:
            self._fts_available = False
            return
        try:
            connection.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
                USING fts5(memory_id UNINDEXED, project, title, kind, content, tags)
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
            connection.execute("SELECT rowid FROM memories_fts LIMIT 1").fetchall()
            return True
        except sqlite3.OperationalError:
            self._fts_available = False
            return False

    def _index_memory(self, connection: sqlite3.Connection, memory: Memory) -> None:
        if not self._has_fts(connection):
            return
        try:
            connection.execute("DELETE FROM memories_fts WHERE memory_id = ?", (memory.id,))
            connection.execute(
                """
                INSERT INTO memories_fts (memory_id, project, title, kind, content, tags)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    memory.id,
                    memory.project,
                    memory.title,
                    memory.kind,
                    memory.content,
                    " ".join(memory.tags),
                ),
            )
        except sqlite3.OperationalError:
            self._rebuild_fts(connection)

    def _rebuild_fts(self, connection: sqlite3.Connection) -> None:
        if not self._fts_enabled or not self._fts_available:
            return
        connection.execute("DELETE FROM memories_fts")
        rows = connection.execute("SELECT * FROM memories").fetchall()
        for row in rows:
            memory = self._row_to_memory(row)
            connection.execute(
                """
                INSERT INTO memories_fts (memory_id, project, title, kind, content, tags)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    memory.id,
                    memory.project,
                    memory.title,
                    memory.kind,
                    memory.content,
                    " ".join(memory.tags),
                ),
            )

    def _search_fts(
        self,
        connection: sqlite3.Connection,
        query: str,
        project: str | None,
        limit: int,
    ) -> list[sqlite3.Row]:
        params: list[object] = [_quote_fts_query(query)]
        sql = """
            SELECT DISTINCT m.*
            FROM memories_fts f
            JOIN memories m ON m.id = f.memory_id
            WHERE memories_fts MATCH ?
        """
        if project is not None:
            sql += " AND m.project = ?"
            params.append(project)
        sql += " ORDER BY m.updated_at DESC LIMIT ?"
        params.append(limit)
        try:
            return list(connection.execute(sql, params).fetchall())
        except sqlite3.OperationalError:
            return self._search_like(connection, query, project, limit)

    def _search_like(
        self,
        connection: sqlite3.Connection,
        query: str,
        project: str | None,
        limit: int,
    ) -> list[sqlite3.Row]:
        pattern = f"%{query}%"
        params: list[object] = [pattern, pattern, pattern, pattern, pattern]
        sql = """
            SELECT *
            FROM memories
            WHERE (
                project LIKE ?
                OR title LIKE ?
                OR kind LIKE ?
                OR content LIKE ?
                OR tags LIKE ?
            )
        """
        if project is not None:
            sql += " AND project = ?"
            params.append(project)
        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        return list(connection.execute(sql, params).fetchall())

    def _row_to_memory(self, row: sqlite3.Row) -> Memory:
        return Memory(
            id=row["id"],
            project=row["project"],
            title=row["title"],
            kind=row["kind"],
            content=row["content"],
            tags=json.loads(row["tags"] or "[]"),
            source=row["source"],
            confidence=float(row["confidence"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _quote_fts_query(query: str) -> str:
    escaped = query.replace('"', '""')
    return f'"{escaped}"'


def _memories_to_json(memories: list[Memory]) -> str:
    return json.dumps({"memories": [memory.model_dump() for memory in memories]}, indent=2)
