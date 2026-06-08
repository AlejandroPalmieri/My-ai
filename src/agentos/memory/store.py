from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel


class Memory(BaseModel):
    id: int
    project: str
    title: str
    kind: str
    content: str
    tags: list[str]
    created_at: str
    updated_at: str


class MemoryStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.agentos_dir = root / ".agentos"
        self.db_path = self.agentos_dir / "memory.db"
        self.agentos_dir.mkdir(parents=True, exist_ok=True)
        self._fts_available = False
        self._ensure_schema()

    def add_memory(
        self,
        project: str,
        title: str,
        kind: str,
        content: str,
        tags: list[str],
    ) -> Memory:
        now = datetime.now(UTC).isoformat()
        tags_json = json.dumps(tags)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO memories (project, title, kind, content, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (project, title, kind, content, tags_json, now, now),
            )
            memory_id = int(cursor.lastrowid)
            if self._has_fts(connection):
                connection.execute(
                    """
                    INSERT INTO memories_fts (rowid, title, content, tags)
                    VALUES (?, ?, ?, ?)
                    """,
                    (memory_id, title, content, " ".join(tags)),
                )
            row = connection.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        return self._row_to_memory(row)

    def search(self, query: str, project: str | None = None, limit: int = 20) -> list[Memory]:
        with self._connect() as connection:
            if self._has_fts(connection):
                rows = self._search_fts(connection, query, project, limit)
            else:
                rows = self._search_like(connection, query, project, limit)
        return [self._row_to_memory(row) for row in rows]

    def list_memories(self) -> list[Memory]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM memories ORDER BY id").fetchall()
        return [self._row_to_memory(row) for row in rows]

    def export_json(self, path: Path) -> int:
        memories = self.list_memories()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {"memories": [memory.model_dump() for memory in memories]},
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return len(memories)

    def export_json_text(self) -> str:
        memories = self.list_memories()
        return json.dumps({"memories": [memory.model_dump() for memory in memories]}, indent=2)

    def import_json(self, path: Path) -> int:
        data = json.loads(path.read_text(encoding="utf-8"))
        count = 0
        for item in data.get("memories", []):
            self.add_memory(
                project=item["project"],
                title=item["title"],
                kind=item["kind"],
                content=item["content"],
                tags=list(item.get("tags", [])),
            )
            count += 1
        return count

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project TEXT NOT NULL,
                    title TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            try:
                connection.execute(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
                    USING fts5(title, content, tags, content='memories', content_rowid='id')
                    """
                )
                self._fts_available = True
            except sqlite3.OperationalError:
                self._fts_available = False

    def _has_fts(self, connection: sqlite3.Connection) -> bool:
        if not self._fts_available:
            return False
        try:
            connection.execute("SELECT rowid FROM memories_fts LIMIT 1").fetchall()
            return True
        except sqlite3.OperationalError:
            self._fts_available = False
            return False

    def _search_fts(
        self,
        connection: sqlite3.Connection,
        query: str,
        project: str | None,
        limit: int,
    ) -> list[sqlite3.Row]:
        params: list[object] = [_quote_fts_query(query)]
        sql = """
            SELECT m.*
            FROM memories_fts f
            JOIN memories m ON m.id = f.rowid
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
        params: list[object] = [pattern, pattern, pattern]
        sql = """
            SELECT *
            FROM memories
            WHERE (title LIKE ? OR content LIKE ? OR tags LIKE ?)
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
            tags=json.loads(row["tags"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


def _quote_fts_query(query: str) -> str:
    escaped = query.replace('"', '""')
    return f'"{escaped}"'
