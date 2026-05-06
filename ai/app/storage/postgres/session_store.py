from __future__ import annotations

import json
from typing import Any, Callable

from app.core.time import utc_now
from app.core.utils.ids import new_id


class PostgresSessionStore:
    """agent transcript를 Postgres agent_sessions/agent_messages에 저장한다.

    TranscriptStore 호출부와 같은 응답 형태를 유지해 agent.loop replay 코드를 크게 흔들지 않는다.
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
        if system_prompt and not metadata_payload.get("system_prompt_snapshot"):
            metadata_payload["system_prompt_snapshot"] = system_prompt
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
                session_role, session_source, history_version, running_task_run_id, workspace_key,
                status, title, metadata, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, 0, NULL, %s, 'ACTIVE', %s, %s::jsonb, now(), now())
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
                source,
                metadata_payload.get("workspace_key"),
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
        raise ValueError("owner_key is required")

    def append_user_message_and_start_task(
        self,
        *,
        owner_key: str,
        session_id: str,
        content: str,
        client_message_id: str,
        task_run_id: str,
        base_history_version: int,
    ) -> dict[str, Any]:
        connection = self.connection_factory()
        session_row = connection.execute(
            """
            SELECT * FROM agent_sessions
            WHERE session_id = %s AND owner_key = %s
            FOR UPDATE
            """,
            (session_id, owner_key),
        ).fetchone()
        self._ensure_product_session_row(session_row, session_id=session_id)

        duplicate_row = connection.execute(
            """
            SELECT * FROM agent_messages
            WHERE session_id = %s
              AND role = 'user'
              AND metadata->>'client_message_id' = %s
            ORDER BY message_sequence ASC
            LIMIT 1
            """,
            (session_id, client_message_id),
        ).fetchone()
        if duplicate_row is not None:
            metadata = _json_load(duplicate_row.get("metadata"), {})
            current_version = int(session_row.get("history_version") or 0)
            connection.commit()
            return {
                "duplicate": True,
                "session_id": session_id,
                "message_id": duplicate_row.get("message_sequence"),
                "message_uuid": duplicate_row.get("message_id"),
                "task_run_id": metadata.get("task_run_id") or task_run_id,
                "base_history_version": max(0, current_version - 1),
                "after_user_message_version": current_version,
                "completion_expected_version": current_version,
                "running_task_run_id": session_row.get("running_task_run_id"),
            }

        current_version = int(session_row.get("history_version") or 0)
        if current_version != int(base_history_version):
            raise ValueError("history version mismatch")
        if session_row.get("running_task_run_id"):
            raise ValueError("session already has a running task")

        sequence = self._next_message_sequence(connection, session_id)
        message_id = new_id("msg")
        metadata_payload = {
            "source": "api.session",
            "client_message_id": client_message_id,
            "task_run_id": task_run_id,
        }
        # product session row lock은 Redis projection보다 영속 기준에 가깝다.
        # 프로세스가 죽어도 running_task_run_id가 남아 중복 append를 막고,
        # 다음 명령은 TaskRun 상태를 확인한 뒤 stale guard만 정리한다.
        connection.execute(
            """
            INSERT INTO agent_messages (
                message_id, session_id, message_sequence, role, content, metadata, created_at
            )
            VALUES (%s, %s, %s, 'user', %s::jsonb, %s::jsonb, now())
            """,
            (message_id, session_id, sequence, _json({"text": content}), _json(metadata_payload)),
        )
        after_version = current_version + 1
        connection.execute(
            """
            UPDATE agent_sessions
            SET history_version = %s,
                running_task_run_id = %s,
                updated_at = now(),
                metadata = jsonb_set(
                    metadata,
                    '{message_count}',
                    to_jsonb(COALESCE((metadata->>'message_count')::int, 0) + 1),
                    true
                )
            WHERE session_id = %s AND owner_key = %s
            """,
            (after_version, task_run_id, session_id, owner_key),
        )
        connection.commit()
        return {
            "duplicate": False,
            "session_id": session_id,
            "message_id": sequence,
            "message_uuid": message_id,
            "task_run_id": task_run_id,
            "base_history_version": current_version,
            "after_user_message_version": after_version,
            "completion_expected_version": after_version,
            "running_task_run_id": task_run_id,
        }

    def append_assistant_message_and_finish_task(
        self,
        *,
        owner_key: str,
        session_id: str,
        task_run_id: str,
        content: str,
        completion_expected_version: int,
        status: str,
    ) -> dict[str, Any]:
        connection = self.connection_factory()
        session_row = connection.execute(
            """
            SELECT * FROM agent_sessions
            WHERE session_id = %s AND owner_key = %s
            FOR UPDATE
            """,
            (session_id, owner_key),
        ).fetchone()
        self._ensure_product_session_row(session_row, session_id=session_id)
        if session_row.get("running_task_run_id") != task_run_id:
            raise ValueError("task does not own session running guard")
        current_version = int(session_row.get("history_version") or 0)
        if current_version != int(completion_expected_version):
            raise ValueError("history version mismatch")

        sequence = self._next_message_sequence(connection, session_id)
        message_id = new_id("msg")
        metadata_payload = {"source": "api.session", "task_run_id": task_run_id, "status": status}
        connection.execute(
            """
            INSERT INTO agent_messages (
                message_id, session_id, message_sequence, role, content, metadata, created_at
            )
            VALUES (%s, %s, %s, 'assistant', %s::jsonb, %s::jsonb, now())
            """,
            (message_id, session_id, sequence, _json({"text": content}), _json(metadata_payload)),
        )
        result_version = current_version + 1
        connection.execute(
            """
            UPDATE agent_sessions
            SET history_version = %s,
                running_task_run_id = NULL,
                updated_at = now(),
                metadata = jsonb_set(
                    metadata,
                    '{message_count}',
                    to_jsonb(COALESCE((metadata->>'message_count')::int, 0) + 1),
                    true
                )
            WHERE session_id = %s AND owner_key = %s
            """,
            (result_version, session_id, owner_key),
        )
        connection.commit()
        return {
            "session_id": session_id,
            "message_id": sequence,
            "message_uuid": message_id,
            "task_run_id": task_run_id,
            "completion_expected_version": completion_expected_version,
            "completion_result_version": result_version,
        }

    def clear_stale_running_task(
        self,
        *,
        owner_key: str,
        session_id: str,
        task_run_id: str,
    ) -> bool:
        connection = self.connection_factory()
        row = connection.execute(
            """
            UPDATE agent_sessions
            SET running_task_run_id = NULL,
                updated_at = now()
            WHERE session_id = %s
              AND owner_key = %s
              AND running_task_run_id = %s
            RETURNING session_id
            """,
            (session_id, owner_key, task_run_id),
        ).fetchone()
        connection.commit()
        return row is not None

    def search_public_sessions(
        self,
        query: str,
        *,
        owner_key: str,
        workspace_key: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        if not owner_key:
            raise ValueError("owner_key is required")
        return self._search_sessions_by_source(query, source="api.session", owner_key=owner_key, workspace_key=workspace_key, limit=limit)

    def search_transcript_sessions(self, query: str, *, owner_key: str, limit: int = 10) -> list[dict[str, Any]]:
        if not owner_key:
            raise ValueError("owner_key is required")
        return self._search_sessions_by_source(query, source="agent.loop", owner_key=owner_key, workspace_key=None, limit=limit)

    def close(self) -> None:
        """connection_factory가 요청마다 연결을 만들기 때문에 저장소 자체 close는 no-op이다."""

    def _next_message_sequence(self, connection: Any, session_id: str) -> int:
        sequence_row = connection.execute(
            "SELECT COALESCE(MAX(message_sequence), 0) + 1 AS next_sequence FROM agent_messages WHERE session_id = %s",
            (session_id,),
        ).fetchone()
        return int((sequence_row or {}).get("next_sequence") or 1)

    def _ensure_product_session_row(self, row: Any, *, session_id: str) -> None:
        if row is None:
            raise KeyError(session_id)
        metadata = _json_load(row.get("metadata"), {})
        source = row.get("session_source") or metadata.get("source") or row.get("session_role")
        if source != "api.session":
            raise ValueError("session is not a public product session")

    def _search_sessions_by_source(
        self,
        query: str,
        *,
        source: str,
        owner_key: str | None,
        workspace_key: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        where = ["COALESCE(s.session_source, s.metadata->>'source') = %s", "COALESCE(m.content->>'text', '') ILIKE %s"]
        params: list[Any] = [source, f"%{query}%"]
        if owner_key is not None:
            where.append("s.owner_key = %s")
            params.append(owner_key)
        if workspace_key is not None:
            where.append("s.workspace_key = %s")
            params.append(workspace_key)
        connection = self.connection_factory()
        rows = connection.execute(
            f"""
            SELECT DISTINCT s.*, m.content->>'text' AS preview
            FROM agent_messages m
            JOIN agent_sessions s ON s.session_id = m.session_id
            WHERE {" AND ".join(where)}
            ORDER BY s.updated_at DESC, s.created_at DESC
            LIMIT %s
            """,
            tuple([*params, limit]),
        ).fetchall()
        results = []
        for row in rows:
            record = _session_from_row(row)
            if record is not None:
                record["preview"] = row.get("preview")
                results.append(record)
        return results


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
        "source": row.get("session_source") or metadata.get("source") or row.get("session_role"),
        "session_source": row.get("session_source") or metadata.get("source") or row.get("session_role"),
        "user_id": metadata.get("user_id") or row.get("owner_key"),
        "owner_key": row.get("owner_key"),
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
        "history_version": int(row.get("history_version") or 0),
        "running_task_run_id": row.get("running_task_run_id"),
        "workspace_key": row.get("workspace_key"),
    }


def _message_from_row(row: Any) -> dict[str, Any]:
    content = _json_load(row.get("content"), {})
    metadata = _json_load(row.get("metadata"), {})
    return {
        "id": row.get("message_sequence"),
        "message_id": row.get("message_id"),
        "message_sequence": row.get("message_sequence"),
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
