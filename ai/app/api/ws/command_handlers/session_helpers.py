"""공통 세션 헬퍼 함수들.

commands.py에 있던 세션 관련 모듈 레벨 순수 함수들을 여기로 이동한다.
WebSocketCommandRouter 클래스 메서드가 아닌, 세션 상태 조회·수정 관련 유틸리티다.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from dataclasses import asdict, is_dataclass
from pydantic import BaseModel

from app.api.ws.command_handlers.constants import (
    OPENAI_MODEL_FALLBACKS,
    PROTECTED_SESSION_METADATA_KEYS,
    PUBLIC_SESSION_SOURCE,
    PUBLIC_SESSION_TOOLSETS,
    SESSION_METADATA_PATCH_ALLOWLIST,
    SESSION_SETTINGS_ALLOWLIST,
    TASK_TRANSCRIPT_SOURCE,
)
from app.api.ws.command_types import WebSocketCommandContext, WebSocketCommandError
from app.core.time import utc_now
from app.core.utils.ids import new_id
from app.domain.orchestration.run_lifecycle import classify_task_run_liveness
from app.domain.session.session_runtime_state import get_system_prompt_snapshot


# ── 세션 조회 / 상태 검사 ──────────────────────────────────────────────

def get_public_session(context: WebSocketCommandContext, session_id: str, *, allow_deleted: bool = False) -> dict[str, Any]:
    """공개 세션을 가져오고 없으면 WebSocketCommandError를 일으킨다."""
    session = context.websocket.app.state.session_store.get_session(session_id)
    if session is None or not is_public_session(session, allow_deleted=allow_deleted):
        raise WebSocketCommandError("not_found", "session not found")
    return session


def is_public_session(session: dict[str, Any], *, allow_deleted: bool = False) -> bool:
    metadata = dict(session.get("metadata") or {})
    if session.get("deleted_at") is not None and not allow_deleted:
        return False
    return session.get("source") == PUBLIC_SESSION_SOURCE or metadata.get("source") == PUBLIC_SESSION_SOURCE


def ensure_session_idle(session: dict[str, Any]) -> None:
    if session.get("running_task_run_id"):
        raise WebSocketCommandError("conflict", "session has a running task", retryable=True)


def refresh_stale_running_guard(context: WebSocketCommandContext, session: dict[str, Any]) -> dict[str, Any]:
    task_run_id = session.get("running_task_run_id")
    if not task_run_id:
        return session
    task = context.websocket.app.state.repository.get_task(str(task_run_id))
    liveness = classify_task_run_liveness(task)
    if liveness.blocks_session:
        return session
    recover_stale_task_if_needed(context.websocket.app.state.repository, task, liveness=liveness)
    context.websocket.app.state.session_store.clear_stale_running_task(
        owner_key=str(session.get("user_id") or context.auth.user_id),
        session_id=str(session["id"]),
        task_run_id=str(task_run_id),
    )
    refreshed = context.websocket.app.state.session_store.get_session(str(session["id"]))
    return refreshed or session


def recover_stale_task_if_needed(repository: Any, task: Any, *, liveness: Any | None = None) -> None:
    if task is None:
        return
    current_liveness = liveness or classify_task_run_liveness(task)
    if not current_liveness.should_recover:
        return
    recover = getattr(repository, "recover_stale_task_run", None)
    if recover is None:
        return
    recover(str(task.task_run_id), reason=str(current_liveness.reason))


# ── 세션 생성 ───────────────────────────────────────────────────────────

def create_public_session(
    context: WebSocketCommandContext,
    *,
    content: str,
    model: str | None,
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    session_id = new_id("session")
    metadata: dict[str, Any] = {"source": PUBLIC_SESSION_SOURCE}
    if context.auth.workspace_key:
        metadata["workspace_key"] = context.auth.workspace_key
    context.websocket.app.state.session_store.create_session(
        session_id=session_id,
        session_key=session_id,
        source=PUBLIC_SESSION_SOURCE,
        user_id=context.auth.user_id,
        model=model,
        title=derive_session_title(content),
        metadata=metadata,
        settings=settings or {},
    )
    session = context.websocket.app.state.session_store.get_session(session_id)
    if session is None:
        raise WebSocketCommandError("internal_error", "session was not created", retryable=True)
    return session


def create_task_transcript_session(
    session_store: Any,
    *,
    session_id: str,
    owner_key: str,
    title: str | None,
    model: str | None,
) -> str:
    transcript_session_id = new_id("agent_session")
    session_store.create_session(
        session_id=transcript_session_id,
        session_key=session_id,
        source=TASK_TRANSCRIPT_SOURCE,
        user_id=owner_key,
        model=model,
        parent_session_id=session_id,
        title=title,
        metadata={"source": TASK_TRANSCRIPT_SOURCE, "public_session_id": session_id},
    )
    return transcript_session_id


# ── 세션 메시지 조작 ───────────────────────────────────────────────────

def prepare_retry_turn(
    session_store: Any,
    *,
    owner_key: str,
    session_id: str,
    target_message_id: str | None,
) -> dict[str, Any]:
    messages = session_store.list_messages(session_id)
    user_message = select_retry_user_message(messages, target_message_id=target_message_id)
    if user_message is None:
        raise WebSocketCommandError("not_found", "retry target user message not found")
    user_sequence = int(user_message.get("id") or user_message.get("message_sequence") or 0)
    if user_sequence <= 0:
        raise WebSocketCommandError("invalid_state", "retry target message has no sequence")
    trimmed = truncate_public_session_tail(
        session_store,
        owner_key=owner_key,
        session_id=session_id,
        keep_through_message_id=str(user_sequence),
        default_remove_last=False,
    )
    task_run_id = new_id("task")
    start_existing_user_message_task(
        session_store,
        owner_key=owner_key,
        session_id=session_id,
        task_run_id=task_run_id,
        expected_history_version=trimmed["history_version"],
    )
    refreshed = session_store.list_messages(session_id)
    return {
        "task_run_id": task_run_id,
        "user_message_id": user_sequence,
        "content": str(user_message.get("content") or ""),
        "history_rows": [message for message in refreshed if int(message.get("id") or 0) < user_sequence],
        "base_history_version": trimmed["history_version"],
        "completion_expected_version": trimmed["history_version"],
    }


def select_retry_user_message(
    messages: list[dict[str, Any]],
    *,
    target_message_id: str | None,
) -> dict[str, Any] | None:
    if target_message_id:
        for message in messages:
            if message_matches_client_ref(message, target_message_id) and message.get("role") == "user":
                return message
        return None
    for message in reversed(messages):
        if message.get("role") == "user":
            return message
    return None


def message_matches_client_ref(message: dict[str, Any], message_ref: str) -> bool:
    candidates = {
        str(message.get("id") or ""),
        str(message.get("message_id") or ""),
        str(message.get("messageId") or ""),
        str(message.get("message_sequence") or ""),
    }
    return message_ref in candidates


def truncate_public_session_tail(
    session_store: Any,
    *,
    owner_key: str,
    session_id: str,
    keep_through_message_id: str | None,
    default_remove_last: bool,
) -> dict[str, Any]:
    if hasattr(session_store, "connection_factory"):
        return _truncate_postgres_session_tail(
            session_store,
            owner_key=owner_key,
            session_id=session_id,
            keep_through_message_id=keep_through_message_id,
            default_remove_last=default_remove_last,
        )
    return _truncate_memory_session_tail(
        session_store,
        owner_key=owner_key,
        session_id=session_id,
        keep_through_message_id=keep_through_message_id,
        default_remove_last=default_remove_last,
    )


def _truncate_memory_session_tail(
    session_store: Any,
    *,
    owner_key: str,
    session_id: str,
    keep_through_message_id: str | None,
    default_remove_last: bool,
) -> dict[str, Any]:
    session = session_store.get_session(session_id)
    if session is None:
        raise WebSocketCommandError("not_found", "session not found")
    if str(session.get("user_id") or session.get("owner_key") or "") != str(owner_key):
        raise WebSocketCommandError("forbidden", "forbidden")
    messages = session_store.messages.get(session_id, [])
    if keep_through_message_id is None and default_remove_last:
        keep_count = max(0, len(messages) - 1)
    else:
        keep_sequence = _resolve_memory_message_sequence(messages, keep_through_message_id)
        keep_count = len([message for message in messages if int(message.get("id") or 0) <= keep_sequence])
    session_store.messages[session_id] = messages[:keep_count]
    mutable_session = session_store.sessions[session_id]
    mutable_session["message_count"] = keep_count
    mutable_session["history_version"] = int(mutable_session.get("history_version") or 0) + 1
    mutable_session["running_task_run_id"] = None
    mutable_session["updated_at"] = utc_now()
    return {"history_version": mutable_session["history_version"]}


def _resolve_memory_message_sequence(messages: list[dict[str, Any]], message_ref: str | None) -> int:
    if not message_ref:
        return 0
    for message in messages:
        if message_matches_client_ref(message, message_ref):
            return int(message.get("id") or message.get("message_sequence") or 0)
    try:
        return int(message_ref)
    except ValueError as error:
        raise WebSocketCommandError("not_found", "message not found") from error


def _truncate_postgres_session_tail(
    session_store: Any,
    *,
    owner_key: str,
    session_id: str,
    keep_through_message_id: str | None,
    default_remove_last: bool,
) -> dict[str, Any]:
    connection = session_store.connection_factory()
    owner_sql, owner_params = owner_filter(owner_key)
    session_row = connection.execute(
        f"SELECT * FROM agent_sessions WHERE session_id = %s AND {owner_sql} FOR UPDATE",
        tuple([session_id, *owner_params]),
    ).fetchone()
    if session_row is None:
        raise WebSocketCommandError("not_found", "session not found")
    if session_row.get("running_task_run_id"):
        raise WebSocketCommandError("conflict", "session has a running task", retryable=True)
    if keep_through_message_id is None and default_remove_last:
        row = connection.execute(
            "SELECT COALESCE(MAX(message_sequence), 0) - 1 AS keep_sequence FROM agent_messages WHERE session_id = %s",
            (session_id,),
        ).fetchone()
        keep_sequence = max(0, int((row or {}).get("keep_sequence") or 0))
    else:
        keep_sequence = _resolve_postgres_message_sequence(connection, session_id=session_id, message_ref=keep_through_message_id)
    connection.execute(
        "DELETE FROM agent_messages WHERE session_id = %s AND message_sequence > %s",
        (session_id, keep_sequence),
    )
    count_row = connection.execute(
        "SELECT COUNT(*) AS count FROM agent_messages WHERE session_id = %s",
        (session_id,),
    ).fetchone()
    next_version = int(session_row.get("history_version") or 0) + 1
    connection.execute(
        f"""
        UPDATE agent_sessions
        SET history_version = %s,
            running_task_run_id = NULL,
            updated_at = now(),
            metadata = jsonb_set(metadata, '{{message_count}}', to_jsonb(%s::int), true)
        WHERE session_id = %s AND {owner_sql}
        """,
        tuple([next_version, int((count_row or {}).get("count") or 0), session_id, *owner_params]),
    )
    connection.commit()
    return {"history_version": next_version}


def _resolve_postgres_message_sequence(connection: Any, *, session_id: str, message_ref: str | None) -> int:
    if not message_ref:
        return 0
    row = connection.execute(
        """
        SELECT message_sequence
        FROM agent_messages
        WHERE session_id = %s
          AND (message_id = %s OR message_sequence::text = %s)
        ORDER BY message_sequence ASC
        LIMIT 1
        """,
        (session_id, message_ref, message_ref),
    ).fetchone()
    if row is not None:
        return int(row.get("message_sequence") or 0)
    try:
        return int(message_ref)
    except ValueError as error:
        raise WebSocketCommandError("not_found", "message not found") from error


def start_existing_user_message_task(
    session_store: Any,
    *,
    owner_key: str,
    session_id: str,
    task_run_id: str,
    expected_history_version: int,
) -> None:
    if hasattr(session_store, "connection_factory"):
        connection = session_store.connection_factory()
        owner_sql, owner_params = owner_filter(owner_key)
        row = connection.execute(
            f"""
            UPDATE agent_sessions
            SET running_task_run_id = %s,
                updated_at = now()
            WHERE session_id = %s
              AND {owner_sql}
              AND history_version = %s
              AND running_task_run_id IS NULL
            RETURNING session_id
            """,
            tuple([task_run_id, session_id, *owner_params, expected_history_version]),
        ).fetchone()
        connection.commit()
        if row is None:
            raise WebSocketCommandError("conflict", "session history changed", retryable=True)
        return
    session = session_store.sessions.get(session_id)
    if session is None or str(session.get("user_id") or "") != str(owner_key):
        raise WebSocketCommandError("not_found", "session not found")
    if int(session.get("history_version") or 0) != expected_history_version or session.get("running_task_run_id"):
        raise WebSocketCommandError("conflict", "session history changed", retryable=True)
    session["running_task_run_id"] = task_run_id


# ── 세션 설정 / 메타데이터 ─────────────────────────────────────────────

def update_public_session_title(session_store: Any, *, owner_key: str, session_id: str, title: str) -> None:
    if hasattr(session_store, "update_title"):
        session_store.update_title(owner_key=owner_key, session_id=session_id, title=title)
        return
    if hasattr(session_store, "connection_factory"):
        connection = session_store.connection_factory()
        owner_sql, owner_params = owner_filter(owner_key)
        connection.execute(
            f"UPDATE agent_sessions SET title = %s, updated_at = now() WHERE session_id = %s AND {owner_sql} AND deleted_at IS NULL",
            tuple([title, session_id, *owner_params]),
        )
        connection.commit()
        return
    session = session_store.sessions.get(session_id)
    if session is not None and str(session.get("user_id") or "") == str(owner_key):
        session["title"] = title
        session["updated_at"] = utc_now()


def patch_public_session_metadata(
    session_store: Any,
    *,
    owner_key: str,
    session_id: str,
    metadata_patch: dict[str, Any],
    bump_history_version: bool,
) -> dict[str, Any]:
    if hasattr(session_store, "connection_factory"):
        connection = session_store.connection_factory()
        owner_sql, owner_params = owner_filter(owner_key)
        row = connection.execute(
            f"SELECT metadata, history_version FROM agent_sessions WHERE session_id = %s AND {owner_sql} FOR UPDATE",
            tuple([session_id, *owner_params]),
        ).fetchone()
        if row is None:
            raise WebSocketCommandError("not_found", "session not found")
        metadata = json_load(row.get("metadata"), {})
        metadata.update(metadata_patch)
        next_version = int(row.get("history_version") or 0) + (1 if bump_history_version else 0)
        connection.execute(
            f"""
            UPDATE agent_sessions
            SET metadata = %s::jsonb,
                history_version = %s,
                updated_at = now()
            WHERE session_id = %s AND {owner_sql}
              AND deleted_at IS NULL
            """,
            tuple([json_dumps(metadata), next_version, session_id, *owner_params]),
        )
        connection.commit()
        return {"history_version": next_version, "metadata": metadata}
    session = session_store.sessions.get(session_id)
    if session is None or str(session.get("user_id") or "") != str(owner_key):
        raise WebSocketCommandError("not_found", "session not found")
    metadata = dict(session.get("metadata") or {})
    metadata.update(metadata_patch)
    session["metadata"] = metadata
    if bump_history_version:
        session["history_version"] = int(session.get("history_version") or 0) + 1
    session["updated_at"] = utc_now()
    return {"history_version": int(session.get("history_version") or 0), "metadata": metadata}


def validate_metadata_patch(metadata_patch: dict[str, Any]) -> None:
    protected = PROTECTED_SESSION_METADATA_KEYS.intersection(metadata_patch)
    if protected:
        raise WebSocketCommandError("invalid_payload", "metadataPatch contains protected fields")
    unknown = set(metadata_patch) - SESSION_METADATA_PATCH_ALLOWLIST
    if unknown:
        raise WebSocketCommandError("invalid_payload", "metadataPatch contains unsupported fields")


def normalize_session_settings(settings: dict[str, Any]) -> dict[str, Any]:
    unknown = set(settings) - SESSION_SETTINGS_ALLOWLIST
    if unknown:
        raise WebSocketCommandError("invalid_payload", "settings contains unsupported fields")
    normalized: dict[str, Any] = {}
    model = settings.get("model")
    if model is not None:
        if not isinstance(model, str) or not model.strip():
            raise WebSocketCommandError("invalid_payload", "settings.model must be a non-empty string")
        normalized["model"] = model.strip()
    system_prompt = settings.get("systemPrompt", settings.get("system_prompt"))
    if system_prompt is not None:
        if not isinstance(system_prompt, str):
            raise WebSocketCommandError("invalid_payload", "settings.systemPrompt must be a string")
        normalized["systemPrompt"] = system_prompt
    toolsets = settings.get("toolsets")
    if toolsets is not None:
        if not isinstance(toolsets, list) or any(not isinstance(item, str) or not item.strip() for item in toolsets):
            raise WebSocketCommandError("invalid_payload", "settings.toolsets must be a string array")
        normalized_toolsets = [item.strip() for item in toolsets]
        if any(item not in PUBLIC_SESSION_TOOLSETS for item in normalized_toolsets):
            raise WebSocketCommandError("invalid_payload", "settings.toolsets contains unsupported toolsets")
        normalized["toolsets"] = normalized_toolsets
    delegation_policy = settings.get("delegationPolicy", settings.get("delegation_policy"))
    if delegation_policy is not None:
        if not isinstance(delegation_policy, dict):
            raise WebSocketCommandError("invalid_payload", "settings.delegationPolicy must be an object")
        normalized["delegationPolicy"] = normalize_delegation_policy(delegation_policy)
    return normalized


def normalize_delegation_policy(policy: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = {"canDelegate", "maxWorkerDepth"}
    if set(policy) - allowed_keys:
        raise WebSocketCommandError("invalid_payload", "settings.delegationPolicy contains unsupported fields")
    can_delegate = policy.get("canDelegate", False)
    if not isinstance(can_delegate, bool):
        raise WebSocketCommandError("invalid_payload", "settings.delegationPolicy.canDelegate must be a boolean")
    max_worker_depth = policy.get("maxWorkerDepth", 0)
    if not isinstance(max_worker_depth, int) or max_worker_depth < 0 or max_worker_depth > 1:
        raise WebSocketCommandError("invalid_payload", "settings.delegationPolicy.maxWorkerDepth must be 0 or 1")
    return {"canDelegate": can_delegate, "maxWorkerDepth": max_worker_depth}


def session_settings_snapshot(session: dict[str, Any]) -> dict[str, Any]:
    settings = session.get("settings")
    if not isinstance(settings, dict):
        return {}
    return dict(settings)


def apply_session_settings_snapshot(
    task_input: dict[str, Any],
    settings: dict[str, Any],
    *,
    session: dict[str, Any],
) -> None:
    """세션 설정을 TaskRun 입력에 복사해 이후 재시작/재생 시 같은 실행 기준을 유지한다."""
    snapshot = dict(settings)
    task_input["settings_snapshot"] = snapshot
    if "model" in snapshot and not task_input.get("model"):
        task_input["model"] = snapshot["model"]
    if "toolsets" in snapshot:
        task_input["toolsets"] = list(snapshot["toolsets"])
        task_input["enabled_toolsets"] = list(snapshot["toolsets"])
    if "delegationPolicy" in snapshot:
        task_input["delegation_policy"] = dict(snapshot["delegationPolicy"])
    task_input["system_prompt_snapshot"] = get_system_prompt_snapshot(session)


def default_agent_loop_toolsets(state: Any) -> tuple[str, ...]:
    tool_catalog = getattr(state, "tool_catalog", None)
    default_toolsets = getattr(tool_catalog, "default_toolsets", None)
    if isinstance(default_toolsets, tuple):
        return default_toolsets
    if isinstance(default_toolsets, list):
        return tuple(str(item) for item in default_toolsets if str(item).strip())
    return tuple(sorted(PUBLIC_SESSION_TOOLSETS))


# ── 세션 페이로드 빌더 ─────────────────────────────────────────────────

def public_session_payload(
    session: dict[str, Any],
    *,
    context: WebSocketCommandContext | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "session_id": str(session["id"]),
        "session_key": session.get("session_key"),
        "title": session.get("title"),
        "owner_key": session.get("user_id"),
        "owner_user_id": session.get("owner_user_id"),
        "status": session.get("status"),
        "source": session.get("source"),
        "parent_session_id": session.get("parent_session_id"),
        "message_count": int(session.get("message_count") or 0),
        "history_version": int(session.get("history_version") or 0),
        "metadata": dict(session.get("metadata") or {}),
        "settings": dict(session.get("settings") or {}),
        "created_at": session.get("created_at") or session.get("started_at"),
        "updated_at": session.get("updated_at"),
        "ended_at": session.get("ended_at"),
        "archived_at": session.get("archived_at"),
        "deleted_at": session.get("deleted_at"),
        "purge_after": session.get("purge_after"),
    }
    if context is not None:
        payload.update(_session_list_preview_payload(context, session_id=str(session["id"])))
    return payload


def _session_list_preview_payload(context: WebSocketCommandContext, *, session_id: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "last_message": None,
        "last_message_at": None,
        "active_task_run_id": None,
        "last_task_run_status": None,
    }

    messages = context.websocket.app.state.session_store.list_messages(session_id)
    if messages:
        last_message = messages[-1]
        result["last_message"] = last_message.get("content")
        result["last_message_at"] = last_message.get("timestamp")

    tasks = context.websocket.app.state.repository.list_tasks(session_key=session_id, limit=50, offset=0)
    tasks = [task for task in tasks if not is_expired_running_task(task)]
    if not tasks:
        return result

    active_task = next((task for task in tasks if is_sidebar_active_task(task)), None)
    latest_task = active_task or tasks[0]
    result["last_task_run_status"] = latest_task.status
    if active_task is not None:
        result["active_task_run_id"] = active_task.task_run_id
    return result


# ── 태스크 생명주기 분류 ────────────────────────────────────────────────

def is_sidebar_active_task(task: Any) -> bool:
    return classify_task_run_liveness(task).blocks_session


def is_live_active_task(repository: Any, task: Any) -> bool:
    from app.domain.orchestration.run_lifecycle import classify_task_run_liveness as _clf
    liveness = _clf(task)
    if liveness.reason == "direct_run_without_supervisor_claim" and is_active_direct_run_stale(task):
        return False
    if liveness.blocks_session:
        return True
    recover_stale_task_if_needed(repository, task, liveness=liveness)
    return False


def is_active_direct_run_stale(task: Any) -> bool:
    from app.api.ws.command_handlers.constants import ACTIVE_DIRECT_RUN_TTL_SECONDS
    updated_at = getattr(task, "updated_at", None)
    if not isinstance(updated_at, datetime):
        return False
    return (utc_now() - updated_at).total_seconds() > ACTIVE_DIRECT_RUN_TTL_SECONDS


def is_expired_running_task(task: Any) -> bool:
    liveness = classify_task_run_liveness(task)
    return liveness.should_recover and not liveness.blocks_session


# ── 메시지 페이로드 ──────────────────────────────────────────────────────

def message_payload(message: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(message.get("metadata") or {})
    sequence = int(message["id"])
    durable_message_id = message.get("message_id") or message.get("messageId") or sequence
    return {
        "id": sequence,
        "message_id": str(durable_message_id),
        "message_sequence": sequence,
        "session_id": str(message["session_id"]),
        "role": str(message["role"]),
        "content": message.get("content"),
        "task_run_id": metadata.get("task_run_id") or metadata.get("taskRunId"),
        "client_message_id": metadata.get("client_message_id") or metadata.get("clientMessageId"),
        "metadata": metadata,
        "timestamp": message.get("timestamp"),
        "created_at": message.get("timestamp"),
        "finish_reason": message.get("finish_reason"),
    }


def stored_message_id(session_store: Any, *, session_id: str, stored_ref: Any) -> str:
    stored_ref_text = str(stored_ref)
    for message in session_store.list_messages(session_id):
        mp = message_payload(message)
        if str(mp["id"]) == stored_ref_text or str(mp["message_id"]) == stored_ref_text:
            return str(mp["message_id"])
    return stored_ref_text


def find_accepted_message_by_client_id(
    context: WebSocketCommandContext,
    *,
    session_id: str | None,
    client_message_id: str,
) -> dict[str, Any] | None:
    session_store = context.websocket.app.state.session_store
    candidate_sessions = (
        [session_store.get_session(session_id)]
        if session_id
        else session_store.list_sessions(user_id=context.auth.user_id, limit=10_000, offset=0)
    )
    for session in candidate_sessions:
        if session is None or not is_public_session(session):
            continue
        if str(session.get("user_id") or "") != str(context.auth.user_id):
            continue
        public_session_id = str(session["id"])
        for msg in session_store.list_messages(public_session_id):
            metadata = dict(msg.get("metadata") or {})
            if metadata.get("client_message_id") != client_message_id and metadata.get("clientMessageId") != client_message_id:
                continue
            task_run_id = metadata.get("task_run_id") or metadata.get("taskRunId")
            if not task_run_id:
                continue
            return {
                "session_id": public_session_id,
                "user_message_id": str(message_payload(msg)["message_id"]),
                "assistant_message_id": find_assistant_message_id_for_task(session_store, public_session_id, str(task_run_id)),
                "task_run_id": str(task_run_id),
                "status": task_status_for_payload(context, str(task_run_id)),
                "client_message_id": client_message_id,
            }
    return None


def find_assistant_message_id_for_task(session_store: Any, session_id: str, task_run_id: str) -> str | None:
    for msg in session_store.list_messages(session_id):
        if str(msg.get("role") or "") != "assistant":
            continue
        metadata = dict(msg.get("metadata") or {})
        if str(metadata.get("task_run_id") or metadata.get("taskRunId") or "") == task_run_id:
            return str(message_payload(msg)["message_id"])
    return None


def task_status_for_payload(context: WebSocketCommandContext, task_run_id: str) -> str | None:
    task = context.websocket.app.state.repository.get_task(task_run_id)
    return str(task.status) if task is not None else None


# ── 공통 유틸리티 ─────────────────────────────────────────────────────

def session_command_signature(operation: str, payload: dict[str, Any]) -> str:
    return json.dumps({"operation": operation, "payload": payload}, ensure_ascii=False, sort_keys=True, default=str)


def assistant_content_from_task(task: Any) -> str:
    result_payload = dict(getattr(task, "result_payload", {}) or {})
    for key in ("text", "output_text", "summary", "message", "content"):
        value = result_payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if getattr(task, "progress_summary", None):
        return str(task.progress_summary)
    if getattr(task, "error_message", None):
        return str(task.error_message)
    if getattr(task, "status", None) == "WAITING":
        return "추가 확인이 필요합니다."
    return "요청 처리가 완료되었습니다."


def derive_session_title(content: str) -> str:
    title = " ".join(content.split())
    return title[:60] or "새 AI 대화"


def ensure_owner(context: WebSocketCommandContext, owner_key: Any) -> None:
    if str(owner_key or "") != str(context.auth.user_id):
        raise WebSocketCommandError("forbidden", "forbidden")


def required_str(payload: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    label = keys[0]
    raise WebSocketCommandError("invalid_payload", f"{label} is required")


def optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    raise WebSocketCommandError("invalid_payload", "expected string")


def optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise WebSocketCommandError("invalid_payload", "expected integer")
    try:
        result = int(value)
    except (TypeError, ValueError) as error:
        raise WebSocketCommandError("invalid_payload", "expected integer") from error
    if result < 0:
        raise WebSocketCommandError("invalid_payload", "expected non-negative integer")
    return result


def positive_int(value: Any, *, default: int, maximum: int) -> int:
    result = default if value is None else optional_int(value)
    if result is None or result < 1:
        raise WebSocketCommandError("invalid_payload", "expected positive integer")
    return min(result, maximum)


def jsonable(value: Any) -> Any:
    """값을 JSON 직렬화 가능한 형태로 변환한다."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=False)
    if is_dataclass(value):
        return jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [jsonable(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def json_dumps(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False, sort_keys=True)


def json_load(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, str):
        return json.loads(value)
    return value


def owner_filter(owner_key: str) -> tuple[str, list[Any]]:
    uid = owner_user_id(owner_key)
    if uid is None:
        return "owner_key = %s", [owner_key]
    return "owner_user_id = %s", [uid]


def owner_user_id(value: Any) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


async def list_openai_models_for_user(state: Any, *, user_id: str, fallback_model: str) -> list[str]:
    models: list[str] = []
    registry = getattr(state, "provider_registry", None)
    provider = None
    if registry is not None and hasattr(registry, "get"):
        try:
            provider = registry.get("openai_api")
        except KeyError:
            provider = None
    if provider is not None and hasattr(provider, "list_user_models"):
        try:
            models = await provider.list_user_models(user_id=user_id, model=fallback_model)
        except Exception:
            models = []

    preferred = [fallback_model, *OPENAI_MODEL_FALLBACKS]
    configured = getattr(getattr(state, "settings", None), "openai_allowed_models", None)
    if isinstance(configured, str):
        preferred.extend([item.strip() for item in configured.split(",") if item.strip()])
    elif isinstance(configured, (list, tuple, set)):
        preferred.extend([str(item).strip() for item in configured if str(item).strip()])

    merged: list[str] = []
    seen: set[str] = set()
    for model in [*preferred, *models]:
        model_id = str(model or "").strip()
        if not model_id or model_id in seen:
            continue
        seen.add(model_id)
        merged.append(model_id)
    return merged or [fallback_model]
