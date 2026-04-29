from __future__ import annotations

import json
from typing import Any, Callable

from app.core.time import utc_now
from app.core.utils.ids import new_id


class PostgresSessionStore:
    """agent transcript를 Postgres agent_sessions/agent_messages에 저장한다.

    기존 SessionStore 호출부와 같은 응답 형태를 유지해 agent.loop replay 코드를 크게 흔들지 않는다.
    """

    def __init__(self, connection_factory: Callable[[], Any]) -> None:
        self.connection_factory = connection_factory

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
        metadata_payload = dict(metadata or {})
        metadata_payload.update(
            {
                "source": source,
                "user_id": user_id,
                "model": model,
                "system_prompt": system_prompt,
                "message_count": 0,
            }
        )
        owner_key = user_id or str(metadata_payload.get("owner_key") or "local")
        connection = self.connection_factory()
        connection.execute(
            """
            INSERT INTO agent_sessions (
                session_id, owner_key, session_key, parent_session_id,
                parent_step_run_id, agent_profile_id, agent_profile_version, agent_config_snapshot,
                session_role, status, title, metadata, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, 'ACTIVE', %s, %s::jsonb, now(), now())
            ON CONFLICT (session_id) DO NOTHING
            """,
            (
                session_id,
                owner_key,
                session_key,
                parent_session_id,
                metadata_payload.get("parent_step_run_id"),
                metadata_payload.get("agent_profile_id"),
                int(metadata_payload.get("agent_profile_version") or 1),
                _json(metadata_payload.get("agent_config_snapshot") or {}),
                _session_role(source, metadata_payload),
                title,
                _json(metadata_payload),
            ),
        )
        connection.commit()
        return session_id

    def end_session(self, session_id: str, *, end_reason: str | None = None) -> None:
        connection = self.connection_factory()
        connection.execute(
            """
            UPDATE agent_sessions
            SET status = 'COMPLETED',
                ended_at = COALESCE(ended_at, now()),
                updated_at = now(),
                metadata = jsonb_set(metadata, '{end_reason}', to_jsonb(%s::text), true)
            WHERE session_id = %s AND ended_at IS NULL
            """,
            (end_reason, session_id),
        )
        connection.commit()

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        connection = self.connection_factory()
        row = connection.execute("SELECT * FROM agent_sessions WHERE session_id = %s", (session_id,)).fetchone()
        return _session_from_row(row)

    def list_sessions(
        self,
        owner: str | None = None,
        *,
        user_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        connection = self.connection_factory()
        sql = "SELECT * FROM agent_sessions"
        effective_owner = owner if owner is not None else user_id
        params: tuple[Any, ...]
        if effective_owner is None:
            params = (limit, offset)
        else:
            sql += " WHERE owner_key = %s"
            params = (effective_owner, limit, offset)
        sql += " ORDER BY updated_at DESC, created_at DESC LIMIT %s OFFSET %s"
        rows = connection.execute(sql, params).fetchall()
        return [record for row in rows if (record := _session_from_row(row)) is not None]

    def get_latest_session_by_key(self, session_key: str, *, owner: str | None = None) -> dict[str, Any] | None:
        connection = self.connection_factory()
        sql = "SELECT * FROM agent_sessions WHERE session_key = %s"
        params: tuple[Any, ...] = (session_key,)
        if owner is not None:
            sql += " AND owner_key = %s"
            params = (session_key, owner)
        sql += " ORDER BY created_at DESC LIMIT 1"
        row = connection.execute(sql, params).fetchone()
        return _session_from_row(row)

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
        connection = self.connection_factory()
        sequence_row = connection.execute(
            "SELECT COALESCE(MAX(message_sequence), 0) + 1 AS next_sequence FROM agent_messages WHERE session_id = %s",
            (session_id,),
        ).fetchone()
        sequence = int((sequence_row or {}).get("next_sequence") or 1)
        metadata_payload = dict(metadata or {})
        metadata_payload.update(
            {
                "tool_name": tool_name,
                "tool_call_id": tool_call_id,
                "tool_calls": tool_calls or [],
                "finish_reason": finish_reason,
            }
        )
        connection.execute(
            """
            INSERT INTO agent_messages (
                message_id, session_id, message_sequence, role, content, metadata, created_at
            )
            VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, now())
            """,
            (
                new_id("msg"),
                session_id,
                sequence,
                role,
                _json({"text": content}),
                _json(metadata_payload),
            ),
        )
        connection.execute(
            """
            UPDATE agent_sessions
            SET updated_at = now(),
                metadata = jsonb_set(
                    metadata,
                    '{message_count}',
                    to_jsonb(COALESCE((metadata->>'message_count')::int, 0) + 1),
                    true
                )
            WHERE session_id = %s
            """,
            (session_id,),
        )
        connection.commit()
        return sequence

    def list_messages(self, session_id: str, *, limit: int | None = None) -> list[dict[str, Any]]:
        connection = self.connection_factory()
        sql = "SELECT * FROM agent_messages WHERE session_id = %s ORDER BY message_sequence ASC"
        params: tuple[Any, ...] = (session_id,)
        if limit is not None:
            sql += " LIMIT %s"
            params = (session_id, limit)
        rows = connection.execute(sql, params).fetchall()
        return [_message_from_row(row) for row in rows]

    def search_sessions(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        connection = self.connection_factory()
        rows = connection.execute(
            """
            SELECT DISTINCT s.*, m.content->>'text' AS preview
            FROM agent_messages m
            JOIN agent_sessions s ON s.session_id = m.session_id
            WHERE COALESCE(m.content->>'text', '') ILIKE %s
            ORDER BY s.created_at DESC
            LIMIT %s
            """,
            (f"%{query}%", limit),
        ).fetchall()
        results = []
        for row in rows:
            record = _session_from_row(row)
            if record is not None:
                record["preview"] = row.get("preview")
                results.append(record)
        return results

    def close(self) -> None:
        """connection_factory가 요청마다 연결을 만들기 때문에 저장소 자체 close는 no-op이다."""


def _session_role(source: str, metadata: dict[str, Any]) -> str:
    role = str(metadata.get("session_role") or source or "main")
    if role in {"main", "user_subagent", "worker", "domain"}:
        return role
    return "worker" if "worker" in role else "main"


def _session_from_row(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    metadata = _json_load(row.get("metadata"), {})
    return {
        "id": row["session_id"],
        "session_key": row["session_key"],
        "source": metadata.get("source") or row.get("session_role"),
        "user_id": metadata.get("user_id") or row.get("owner_key"),
        "model": metadata.get("model"),
        "system_prompt": metadata.get("system_prompt"),
        "parent_session_id": row.get("parent_session_id"),
        "parent_step_run_id": row.get("parent_step_run_id"),
        "status": row.get("status"),
        "title": row.get("title"),
        "metadata": metadata,
        "created_at": row.get("created_at"),
        "started_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "ended_at": row.get("ended_at"),
        "end_reason": metadata.get("end_reason"),
        "message_count": int(metadata.get("message_count") or 0),
    }


def _message_from_row(row: Any) -> dict[str, Any]:
    content = _json_load(row.get("content"), {})
    metadata = _json_load(row.get("metadata"), {})
    return {
        "id": row.get("message_sequence"),
        "session_id": row["session_id"],
        "role": row["role"],
        "content": content.get("text"),
        "tool_name": metadata.get("tool_name"),
        "tool_call_id": metadata.get("tool_call_id"),
        "tool_calls": metadata.get("tool_calls") or [],
        "metadata": metadata,
        "timestamp": row.get("created_at"),
        "finish_reason": metadata.get("finish_reason"),
    }


def _json(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False, sort_keys=True)


def _json_load(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, str):
        return json.loads(value)
    return value
