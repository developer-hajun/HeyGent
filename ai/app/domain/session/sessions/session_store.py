from __future__ import annotations

import json
import random
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Callable, TypeVar

T = TypeVar("T")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    session_key TEXT NOT NULL,
    source TEXT NOT NULL,
    user_id TEXT,
    model TEXT,
    system_prompt TEXT,
    parent_session_id TEXT,
    title TEXT,
    metadata_json TEXT,
    started_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    ended_at REAL,
    end_reason TEXT,
    message_count INTEGER DEFAULT 0,
    FOREIGN KEY (parent_session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL,
    content TEXT,
    tool_name TEXT,
    tool_call_id TEXT,
    tool_calls TEXT,
    metadata_json TEXT,
    timestamp REAL NOT NULL,
    finish_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_key ON sessions(session_key, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_source ON sessions(source, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, timestamp);
"""

FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content,
    content=messages,
    content_rowid=id
);

CREATE TRIGGER IF NOT EXISTS messages_fts_insert AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
END;

CREATE TRIGGER IF NOT EXISTS messages_fts_delete AFTER DELETE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.id, old.content);
END;

CREATE TRIGGER IF NOT EXISTS messages_fts_update AFTER UPDATE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.id, old.content);
    INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
END;
"""


class SessionStore:
    """agent.loop transcript와 세션 검색에 쓰는 SQLite 구현체다."""

    _WRITE_MAX_RETRIES = 12
    _WRITE_RETRY_MIN_S = 0.020
    _WRITE_RETRY_MAX_S = 0.150

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False, timeout=1.0, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._fts_enabled = False
        self._init_schema()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.executescript(SCHEMA_SQL)
            try:
                self._conn.executescript(FTS_SQL)
                self._fts_enabled = True
            except sqlite3.OperationalError:
                self._fts_enabled = False

    def _execute_write(self, fn: Callable[[sqlite3.Connection], T]) -> T:
        last_error: Exception | None = None
        for attempt in range(self._WRITE_MAX_RETRIES):
            try:
                with self._lock:
                    self._conn.execute("BEGIN IMMEDIATE")
                    try:
                        result = fn(self._conn)
                        self._conn.commit()
                        return result
                    except BaseException:
                        self._conn.rollback()
                        raise
            except sqlite3.OperationalError as error:
                if "locked" in str(error).lower() or "busy" in str(error).lower():
                    last_error = error
                    if attempt < self._WRITE_MAX_RETRIES - 1:
                        time.sleep(random.uniform(self._WRITE_RETRY_MIN_S, self._WRITE_RETRY_MAX_S))
                        continue
                raise
        raise last_error or sqlite3.OperationalError("session store write failed")

    def create_session(
        self,
        *,
        session_id: str,
        session_key: str,
        source: str,
        user_id: str | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
        parent_session_id: str | None = None,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        now = time.time()

        def _do(conn: sqlite3.Connection) -> None:
            conn.execute(
                """
                INSERT OR IGNORE INTO sessions (
                    id, session_key, source, user_id, model, system_prompt,
                    parent_session_id, title, metadata_json, started_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    session_key,
                    source,
                    user_id,
                    model,
                    system_prompt,
                    parent_session_id,
                    title,
                    json.dumps(metadata, ensure_ascii=False) if metadata else None,
                    now,
                    now,
                ),
            )

        self._execute_write(_do)
        return session_id

    def end_session(self, session_id: str, *, end_reason: str | None = None) -> None:
        now = time.time()

        def _do(conn: sqlite3.Connection) -> None:
            conn.execute(
                "UPDATE sessions SET ended_at = ?, end_reason = ?, updated_at = ? WHERE id = ? AND ended_at IS NULL",
                (now, end_reason, now, session_id),
            )

        self._execute_write(_do)

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return self._row_to_session(row)

    def get_latest_session_by_key(self, session_key: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM sessions WHERE session_key = ? ORDER BY started_at DESC LIMIT 1",
                (session_key,),
            ).fetchone()
        return self._row_to_session(row)

    def append_message(
        self,
        *,
        session_id: str,
        role: str,
        content: str | None,
        tool_name: str | None = None,
        tool_call_id: str | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        finish_reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        now = time.time()

        def _do(conn: sqlite3.Connection) -> int:
            cursor = conn.execute(
                """
                INSERT INTO messages (
                    session_id, role, content, tool_name, tool_call_id, tool_calls,
                    metadata_json, timestamp, finish_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    role,
                    content,
                    tool_name,
                    tool_call_id,
                    json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None,
                    json.dumps(metadata, ensure_ascii=False) if metadata else None,
                    now,
                    finish_reason,
                ),
            )
            conn.execute(
                """
                UPDATE sessions
                SET message_count = message_count + 1, updated_at = ?
                WHERE id = ?
                """,
                (now, session_id),
            )
            return int(cursor.lastrowid)

        return self._execute_write(_do)

    def list_messages(self, session_id: str, *, limit: int | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC"
        params: list[Any] = [session_id]
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)

        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_message(row) for row in rows]

    def search_sessions(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        if not query.strip():
            return []

        sql: str
        params: tuple[Any, ...]
        if self._fts_enabled:
            sql = """
                SELECT DISTINCT s.*, m.content AS preview
                FROM messages_fts f
                JOIN messages m ON m.id = f.rowid
                JOIN sessions s ON s.id = m.session_id
                WHERE messages_fts MATCH ?
                ORDER BY s.started_at DESC
                LIMIT ?
            """
            params = (query, limit)
        else:
            like = f"%{query}%"
            sql = """
                SELECT DISTINCT s.*, m.content AS preview
                FROM messages m
                JOIN sessions s ON s.id = m.session_id
                WHERE COALESCE(m.content, '') LIKE ?
                ORDER BY s.started_at DESC
                LIMIT ?
            """
            params = (like, limit)

        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()

        results: list[dict[str, Any]] = []
        for row in rows:
            record = self._row_to_session(row)
            if record is None:
                continue
            record["preview"] = row["preview"]
            results.append(record)
        return results

    @staticmethod
    def _row_to_session(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        payload = dict(row)
        metadata_json = payload.pop("metadata_json", None)
        payload["metadata"] = json.loads(metadata_json) if metadata_json else {}
        return payload

    @staticmethod
    def _row_to_message(row: sqlite3.Row) -> dict[str, Any]:
        payload = dict(row)
        tool_calls = payload.pop("tool_calls", None)
        metadata_json = payload.pop("metadata_json", None)
        payload["tool_calls"] = json.loads(tool_calls) if tool_calls else []
        payload["metadata"] = json.loads(metadata_json) if metadata_json else {}
        return payload
