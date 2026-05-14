from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel

from app.api.deps.http_auth import authenticate_http_user, ensure_owner
from app.api.deps.openapi_auth import document_bearer_auth
from app.api.http.device_tokens import get_fcm_token
from app.domain.notifications.fcm_sender import send_chat_notification
from app.contracts.session import (
    ArchiveSessionRequest,
    CreateSessionMessageRequest,
    CreateSessionMessageResponse,
    SessionListResponse,
    SessionMessageResponse,
    SessionMessagesResponse,
    SessionResponse,
    UpdateSessionRequest,
    UpdateSessionSettingsRequest,
)
from app.contracts.task.task_status import TaskStatus
from app.core.time import utc_now
from app.core.utils.ids import new_id
from app.domain.orchestration.contracts import OrchestrationRequest
from app.domain.session.conversation_history import build_conversation_history
from app.domain.session.history_compaction import compact_conversation_history
from app.domain.session.session_runtime_state import get_system_prompt_snapshot

router = APIRouter(prefix="/sessions", tags=["sessions"], dependencies=[Depends(document_bearer_auth)])

_PUBLIC_SESSION_SOURCE = "api.session"
_TASK_TRANSCRIPT_SOURCE = "agent.loop"
_ACTIVE_TASK_STATUSES = {status.value for status in (TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.WAITING, TaskStatus.BLOCKED)}
_PROTECTED_SESSION_METADATA_KEYS = {
    "owner_key",
    "ownerUserId",
    "owner_user_id",
    "userId",
    "user_id",
    "source",
    "session_source",
    "messageCount",
    "message_count",
    "runningTaskRunId",
    "running_task_run_id",
    "historyVersion",
    "history_version",
    "archivedAt",
    "archived_at",
    "deletedAt",
    "deleted_at",
    "deletedBy",
    "deleted_by",
    "purgeAfter",
    "purge_after",
    "settings",
}
_SESSION_METADATA_PATCH_ALLOWLIST = {"pinned", "color", "tags", "description", "lastViewedAt", "last_viewed_at", "ui"}
_SESSION_SETTINGS_ALLOWLIST = {"model", "systemPrompt", "system_prompt", "toolsets", "delegationPolicy", "delegation_policy"}
_PUBLIC_SESSION_TOOLSETS = {"skills", "session", "planning", "web", "safe"}


@router.post(
    "/messages",
    response_model=CreateSessionMessageResponse,
    summary="새 세션 자동 생성 후 AI 대화 메시지 보내기",
    description=(
        "첫 사용자 메시지를 저장하면서 AI 대화 세션을 자동으로 만듭니다. "
        "프론트에서 새 대화 버튼을 눌렀을 때 빈 세션 생성 API를 먼저 호출할 필요 없이 이 API만 호출하면 됩니다. "
        "사용자별 공개 세션은 기본 10개까지 허용합니다."
    ),
)
async def create_message_in_new_session(
    request: Request,
    payload: CreateSessionMessageRequest,
) -> CreateSessionMessageResponse:
    user = await authenticate_http_user(request)
    if payload.session_id:
        session = _get_public_session_or_404(request, payload.session_id)
        ensure_owner(user, session.get("user_id"))
    else:
        session = _create_public_session_for_message(request, owner_key=user.user_id, payload=payload)
    return await _create_message_in_session(request, payload, session=session, user=user)


@router.get(
    "",
    response_model=SessionListResponse,
    summary="AI 대화 세션 목록 조회",
    description="현재 사용자의 AI 대화 세션 목록을 최신순으로 조회합니다.",
)
async def list_sessions(
    request: Request,
    page: int = Query(default=1, ge=1, description="페이지 번호입니다. 1부터 시작합니다."),
    page_size: int = Query(default=20, ge=1, le=50, alias="pageSize", description="한 페이지에 가져올 세션 수입니다. 최소 1, 최대 50입니다."),
    include_archived: bool = Query(default=False, alias="includeArchived", description="아카이브된 세션까지 조회할지 여부입니다."),
) -> SessionListResponse:
    user = await authenticate_http_user(request)
    offset = (page - 1) * page_size
    items, total_count = _list_public_sessions(
        request.app.state.session_store,
        owner_key=user.user_id,
        limit=page_size,
        offset=offset,
        include_archived=include_archived,
    )
    return SessionListResponse(
        items=[_session_response(item) for item in items],
        page=page,
        page_size=page_size,
        total_count=total_count,
        has_previous=page > 1,
        has_next=offset + len(items) < total_count,
    )


@router.get(
    "/{sessionId}",
    response_model=SessionResponse,
    summary="AI 대화 세션 상세 조회",
    description="AI 대화 세션의 제목, 메시지 개수, 생성/수정 시각을 조회합니다.",
)
async def get_session(
    request: Request,
    sessionId: str = Path(..., description="조회할 AI 대화 세션 ID입니다."),
) -> SessionResponse:
    user = await authenticate_http_user(request)
    session = _get_public_session_or_404(request, sessionId)
    ensure_owner(user, session.get("user_id"))
    return _session_response(session)


@router.post(
    "/{sessionId}/update",
    response_model=SessionResponse,
    summary="AI 대화 세션 제목/표시 metadata 변경",
    description="세션 소유자만 제목과 허용된 표시용 metadata를 변경할 수 있습니다.",
)
async def update_session(
    request: Request,
    payload: UpdateSessionRequest,
    sessionId: str = Path(..., description="변경할 AI 대화 세션 ID입니다."),
) -> SessionResponse:
    user = await authenticate_http_user(request)
    session = _get_public_session_or_404(request, sessionId)
    ensure_owner(user, session.get("user_id"))
    session = _refresh_stale_running_guard(request, session, owner_key=user.user_id)
    _ensure_session_idle_or_409(session)
    if payload.metadata_patch:
        _validate_metadata_patch(payload.metadata_patch)
    signature = _session_command_signature("session.update", {"title": payload.title, "metadataPatch": payload.metadata_patch})
    replay = _replay_http_session_command(request, owner_key=user.user_id, session_id=sessionId, command_id=payload.client_command_id, signature=signature)
    if replay is not None:
        return _session_response(replay)
    if payload.title:
        _call_session_mutation(
            request.app.state.session_store.update_title,
            owner_key=user.user_id,
            session_id=sessionId,
            title=payload.title,
        )
    if payload.metadata_patch:
        _patch_public_session_metadata(
            request.app.state.session_store,
            owner_key=user.user_id,
            session_id=sessionId,
            metadata_patch=payload.metadata_patch,
        )
    updated = _get_public_session_or_404(request, sessionId)
    _remember_http_session_command(request, owner_key=user.user_id, session_id=sessionId, command_id=payload.client_command_id, signature=signature, session=updated)
    return _session_response(updated)


@router.post(
    "/{sessionId}/archive",
    response_model=SessionResponse,
    summary="AI 대화 세션 아카이브 상태 변경",
    description="아카이브된 세션은 기본 세션 목록에서 제외되지만 보존됩니다.",
)
async def archive_session(
    request: Request,
    payload: ArchiveSessionRequest,
    sessionId: str = Path(..., description="아카이브할 AI 대화 세션 ID입니다."),
) -> SessionResponse:
    user = await authenticate_http_user(request)
    session = _get_public_session_or_404(request, sessionId)
    ensure_owner(user, session.get("user_id"))
    session = _refresh_stale_running_guard(request, session, owner_key=user.user_id)
    _ensure_session_idle_or_409(session)
    signature = _session_command_signature("session.archive", {"archived": payload.archived})
    replay = _replay_http_session_command(request, owner_key=user.user_id, session_id=sessionId, command_id=payload.client_command_id, signature=signature)
    if replay is not None:
        return _session_response(replay)
    updated = _call_session_mutation(
        request.app.state.session_store.archive_session,
        owner_key=user.user_id,
        session_id=sessionId,
        archived=payload.archived,
    )
    _remember_http_session_command(request, owner_key=user.user_id, session_id=sessionId, command_id=payload.client_command_id, signature=signature, session=updated)
    return _session_response(updated)


@router.post(
    "/{sessionId}/settings/update",
    response_model=SessionResponse,
    summary="AI 대화 세션 실행 설정 변경",
    description="model, systemPrompt, toolsets, delegationPolicy 설정을 저장하고 다음 메시지 실행에 스냅샷으로 복사합니다.",
)
async def update_session_settings(
    request: Request,
    payload: UpdateSessionSettingsRequest,
    sessionId: str = Path(..., description="설정을 변경할 AI 대화 세션 ID입니다."),
) -> SessionResponse:
    user = await authenticate_http_user(request)
    session = _get_public_session_or_404(request, sessionId)
    ensure_owner(user, session.get("user_id"))
    session = _refresh_stale_running_guard(request, session, owner_key=user.user_id)
    _ensure_session_idle_or_409(session)
    settings = _normalize_session_settings(payload.settings)
    signature = _session_command_signature("session.settings.update", settings)
    replay = _replay_http_session_command(request, owner_key=user.user_id, session_id=sessionId, command_id=payload.client_command_id, signature=signature)
    if replay is not None:
        return _session_response(replay)
    updated = _call_session_mutation(
        request.app.state.session_store.update_session_settings,
        owner_key=user.user_id,
        session_id=sessionId,
        settings=settings,
    )
    _remember_http_session_command(request, owner_key=user.user_id, session_id=sessionId, command_id=payload.client_command_id, signature=signature, session=updated)
    return _session_response(updated)


@router.delete(
    "/{sessionId}",
    response_model=SessionResponse,
    summary="AI 대화 세션 삭제 요청",
    description="세션을 soft delete로 표시합니다. 메시지와 내부 trace는 보존 기간 동안 물리 삭제하지 않습니다.",
)
async def delete_session(
    request: Request,
    sessionId: str = Path(..., description="삭제할 AI 대화 세션 ID입니다."),
) -> SessionResponse:
    user = await authenticate_http_user(request)
    session = _get_public_session_or_404(request, sessionId, allow_deleted=True)
    ensure_owner(user, session.get("user_id"))
    session = _refresh_stale_running_guard(request, session, owner_key=user.user_id)
    _ensure_session_idle_or_409(session)
    deleted = _call_session_mutation(
        request.app.state.session_store.delete_session,
        owner_key=user.user_id,
        session_id=sessionId,
        deleted_by=user.user_id,
    )
    return _session_response(deleted)


@router.post(
    "/{sessionId}/messages",
    response_model=CreateSessionMessageResponse,
    summary="AI 대화 메시지 보내기",
    description=(
        "사용자 메시지를 세션에 저장하고 TaskRun(사용자 요청 하나의 실행 묶음)을 생성해 실행합니다. "
        "실행이 끝나면 AI 답변도 같은 세션에 assistant 메시지로 저장하고, 응답에는 생성된 taskRunId를 함께 돌려줍니다. "
        "도구 호출과 worker/subagent(하위 AI 실행자)의 내부 기록은 AgentSession(내부 실행 대화 기록 세션)에 따로 남습니다."
    ),
)
async def create_session_message(
    request: Request,
    payload: CreateSessionMessageRequest,
    sessionId: str = Path(..., description="메시지를 보낼 AI 대화 세션 ID입니다."),
) -> CreateSessionMessageResponse:
    user = await authenticate_http_user(request)
    if payload.session_id is not None and payload.session_id != sessionId:
        raise HTTPException(status_code=400, detail="sessionId in path and body must match")
    session = _get_public_session_or_404(request, sessionId)
    ensure_owner(user, session.get("user_id"))
    return await _create_message_in_session(request, payload, session=session, user=user)


async def _create_message_in_session(
    request: Request,
    payload: CreateSessionMessageRequest,
    *,
    session: dict[str, Any],
    user,
) -> CreateSessionMessageResponse:
    sessionId = str(session["id"])
    owner_key = str(session.get("user_id") or user.user_id)
    session_store = request.app.state.session_store
    session = _refresh_stale_running_guard(request, session, owner_key=owner_key)

    base_history_version = int(session.get("history_version") or 0)
    conversation_history = compact_conversation_history(
        build_conversation_history(session_store.list_messages(sessionId))
    )
    settings_snapshot = _session_settings_snapshot(session)
    effective_model = str(settings_snapshot.get("model") or payload.model or "").strip() or None
    task_transcript_session_id = _create_task_transcript_session(
        session_store,
        session_id=sessionId,
        owner_key=owner_key,
        title=session.get("title") or payload.content[:120],
        model=effective_model,
    )
    task_input = dict(payload.input_payload)
    if effective_model and not task_input.get("model"):
        task_input["model"] = effective_model
    task_input["prompt"] = payload.content
    task_input["transcript_session_id"] = task_transcript_session_id
    task_input["conversation_history"] = conversation_history
    task_input["system_prompt_snapshot"] = get_system_prompt_snapshot(session)
    task_input["base_history_version"] = base_history_version
    _apply_session_settings_snapshot(task_input, settings_snapshot, session=session)
    task_run_id = new_id("task")
    client_message_id = payload.client_message_id or new_id("client_msg")
    user_append = session_store.append_user_message_and_start_task(
        owner_key=owner_key,
        session_id=sessionId,
        content=payload.content,
        client_message_id=client_message_id,
        task_run_id=task_run_id,
        base_history_version=base_history_version,
    )
    if user_append.get("duplicate"):
        messages_by_id = {message["id"]: message for message in session_store.list_messages(sessionId)}
        assistant_message_id = _find_assistant_message_id_for_task(session_store, sessionId, str(user_append["task_run_id"]))
        task = request.app.state.repository.get_task(str(user_append["task_run_id"]))
        return CreateSessionMessageResponse(
            session_id=sessionId,
            task_run_id=str(user_append["task_run_id"]),
            status=str(getattr(task, "status", "PENDING")),
            user_message=_message_response(messages_by_id[user_append["message_id"]]),
            assistant_message=_message_response(messages_by_id[assistant_message_id])
            if assistant_message_id is not None and assistant_message_id in messages_by_id
            else None,
        )
    task_input["after_user_message_version"] = user_append["after_user_message_version"]
    task_input["completion_expected_version"] = user_append["completion_expected_version"]
    task_input["client_message_id"] = client_message_id

    try:
        task = await request.app.state.orchestrator.start(
            OrchestrationRequest(
                task_run_id=task_run_id,
                owner_key=owner_key,
                session_key=sessionId,
                input_payload=task_input,
            )
        )
    except KeyError as error:
        session_store.clear_stale_running_task(owner_key=owner_key, session_id=sessionId, task_run_id=task_run_id)
        raise HTTPException(status_code=404, detail=f"unknown execution route: {error.args[0]}") from error
    except ValueError as error:
        session_store.clear_stale_running_task(owner_key=owner_key, session_id=sessionId, task_run_id=task_run_id)
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception:
        session_store.clear_stale_running_task(owner_key=owner_key, session_id=sessionId, task_run_id=task_run_id)
        raise

    assistant_message_id = None
    if task.status == "COMPLETED":
        assistant_content = _assistant_content_from_task(task)
        assistant_append = session_store.append_assistant_message_and_finish_task(
            owner_key=owner_key,
            session_id=sessionId,
            task_run_id=task.task_run_id,
            content=assistant_content,
            completion_expected_version=task_input["completion_expected_version"],
            status=task.status,
        )
        assistant_message_id = assistant_append["message_id"]
        # FCM 푸시 알림 (등록된 토큰이 있을 때만)
        fcm_token = get_fcm_token(owner_key)
        if fcm_token:
            send_chat_notification(fcm_token, session_id=sessionId, content=assistant_content)
    elif task.status != "WAITING":
        session_store.clear_stale_running_task(owner_key=owner_key, session_id=sessionId, task_run_id=task.task_run_id)
    messages_by_id = {message["id"]: message for message in session_store.list_messages(sessionId)}
    return CreateSessionMessageResponse(
        session_id=sessionId,
        task_run_id=task.task_run_id,
        status=task.status,
        user_message=_message_response(messages_by_id[user_append["message_id"]]),
        assistant_message=_message_response(messages_by_id[assistant_message_id]) if assistant_message_id is not None else None,
    )


@router.get(
    "/{sessionId}/messages",
    response_model=SessionMessagesResponse,
    summary="AI 대화 메시지 목록 조회",
    description="AI 대화 세션에 저장된 공개 메시지를 순서대로 조회합니다. 내부 도구 호출 기록은 포함하지 않습니다.",
)
async def list_session_messages(
    request: Request,
    sessionId: str = Path(..., description="메시지를 조회할 AI 대화 세션 ID입니다."),
    after_message_id: int | None = Query(default=None, ge=0, alias="afterMessageId", description="이 메시지 ID보다 큰 메시지만 조회합니다. 처음 조회할 때는 비워 둡니다."),
    limit: int = Query(default=100, ge=1, le=500, description="최대 메시지 개수입니다. 최소 1, 최대 500입니다."),
) -> SessionMessagesResponse:
    user = await authenticate_http_user(request)
    session = _get_public_session_or_404(request, sessionId)
    ensure_owner(user, session.get("user_id"))
    messages = request.app.state.session_store.list_messages(sessionId)
    if after_message_id is not None:
        messages = [message for message in messages if int(message.get("id") or 0) > after_message_id]
    items = [_message_response(message) for message in messages[:limit]]
    return SessionMessagesResponse(
        session_id=sessionId,
        after_message_id=after_message_id,
        limit=limit,
        total_count=len(items),
        next_after_message_id=items[-1].id if items else None,
        items=items,
    )


def _create_task_transcript_session(
    session_store,
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
        source=_TASK_TRANSCRIPT_SOURCE,
        user_id=owner_key,
        model=model,
        parent_session_id=session_id,
        title=title,
        metadata={"source": _TASK_TRANSCRIPT_SOURCE, "public_session_id": session_id},
    )
    return transcript_session_id


def _create_public_session_for_message(
    request: Request,
    *,
    owner_key: str,
    payload: CreateSessionMessageRequest,
) -> dict[str, Any]:
    session_store = request.app.state.session_store
    session_limit = max(1, int(getattr(request.app.state.settings, "public_session_limit_per_user", 10)))
    _, total_count = _list_public_sessions(session_store, owner_key=owner_key, limit=1, offset=0)
    if total_count >= session_limit:
        raise HTTPException(
            status_code=409,
            detail=f"public session limit exceeded: {session_limit}",
        )

    session_id = new_id("session")
    session_store.create_session(
        session_id=session_id,
        session_key=session_id,
        source=_PUBLIC_SESSION_SOURCE,
        user_id=owner_key,
        model=payload.model,
        title=_derive_session_title(payload.content),
        metadata={"source": _PUBLIC_SESSION_SOURCE},
    )
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=500, detail="session was not created")
    return session


def _derive_session_title(content: str) -> str:
    title = " ".join(content.split())
    return title[:60] or "새 AI 대화"


def _get_public_session_or_404(request: Request, session_id: str, *, allow_deleted: bool = False) -> dict[str, Any]:
    session = request.app.state.session_store.get_session(session_id)
    if session is None or not _is_public_session(session, allow_deleted=allow_deleted):
        raise HTTPException(status_code=404, detail="session not found")
    return session


def _refresh_stale_running_guard(request: Request, session: dict[str, Any], *, owner_key: str) -> dict[str, Any]:
    task_run_id = session.get("running_task_run_id")
    if not task_run_id:
        return session
    task = request.app.state.repository.get_task(str(task_run_id))
    if task is not None and str(task.status) in _ACTIVE_TASK_STATUSES:
        raise HTTPException(status_code=409, detail="session has a running task")
    request.app.state.session_store.clear_stale_running_task(
        owner_key=owner_key,
        session_id=str(session["id"]),
        task_run_id=str(task_run_id),
    )
    return request.app.state.session_store.get_session(str(session["id"])) or session


def _ensure_session_idle_or_409(session: dict[str, Any]) -> None:
    if session.get("running_task_run_id"):
        raise HTTPException(status_code=409, detail="session has a running task")


def _is_public_session(session: dict[str, Any], *, allow_deleted: bool = False) -> bool:
    metadata = dict(session.get("metadata") or {})
    if session.get("deleted_at") is not None and not allow_deleted:
        return False
    return session.get("source") == _PUBLIC_SESSION_SOURCE or metadata.get("source") == _PUBLIC_SESSION_SOURCE


def _session_response(session: dict[str, Any]) -> SessionResponse:
    metadata = dict(session.get("metadata") or {})
    metadata.pop("source", None)
    return SessionResponse(
        session_id=str(session["id"]),
        title=session.get("title"),
        owner_key=session.get("user_id"),
        owner_user_id=session.get("owner_user_id"),
        status=session.get("status"),
        source=session.get("source"),
        parent_session_id=session.get("parent_session_id"),
        message_count=int(session.get("message_count") or 0),
        created_at=session.get("started_at"),
        updated_at=session.get("updated_at"),
        ended_at=session.get("ended_at"),
        archived_at=session.get("archived_at"),
        deleted_at=session.get("deleted_at"),
        purge_after=session.get("purge_after"),
        metadata=metadata,
        settings=dict(session.get("settings") or {}),
    )


def _message_response(message: dict[str, Any]) -> SessionMessageResponse:
    metadata = dict(message.get("metadata") or {})
    task_run_id = metadata.get("task_run_id") or metadata.get("taskRunId")
    return SessionMessageResponse(
        id=int(message["id"]),
        session_id=str(message["session_id"]),
        role=str(message["role"]),
        content=message.get("content"),
        task_run_id=str(task_run_id) if task_run_id else None,
        metadata=metadata,
        timestamp=message.get("timestamp"),
    )


def _assistant_content_from_task(task) -> str:
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


def _find_assistant_message_id_for_task(session_store, session_id: str, task_run_id: str) -> int | None:
    for message in session_store.list_messages(session_id):
        if str(message.get("role") or "") != "assistant":
            continue
        metadata = dict(message.get("metadata") or {})
        if str(metadata.get("task_run_id") or metadata.get("taskRunId") or "") == task_run_id:
            return int(message.get("id") or 0)
    return None


def _list_public_sessions(
    store,
    *,
    owner_key: str | None,
    limit: int,
    offset: int,
    include_archived: bool = False,
) -> tuple[list[dict[str, Any]], int]:
    if hasattr(store, "connection_factory"):
        return _list_postgres_public_sessions(
            store,
            owner_key=owner_key,
            limit=limit,
            offset=offset,
            include_archived=include_archived,
        )
    return [], 0


def _list_postgres_public_sessions(
    store,
    *,
    owner_key: str | None,
    limit: int,
    offset: int,
    include_archived: bool = False,
) -> tuple[list[dict[str, Any]], int]:
    where = ["COALESCE(session_source, metadata->>'source') = %s", "deleted_at IS NULL"]
    params: list[Any] = [_PUBLIC_SESSION_SOURCE]
    if not include_archived:
        where.append("archived_at IS NULL")
    if owner_key is not None:
        owner_sql, owner_params = _owner_filter(owner_key)
        where.append(owner_sql)
        params.extend(owner_params)
    where_sql = " AND ".join(where)
    connection = store.connection_factory()
    total_row = connection.execute(f"SELECT COUNT(*) AS count FROM agent_sessions WHERE {where_sql}", tuple(params)).fetchone()
    rows = connection.execute(
        f"SELECT * FROM agent_sessions WHERE {where_sql} ORDER BY updated_at DESC LIMIT %s OFFSET %s",
        tuple([*params, limit, offset]),
    ).fetchall()
    return [_postgres_session_from_row(row) for row in rows], int(_row_get(total_row, "count") or 0)


def _postgres_session_from_row(row: Any) -> dict[str, Any]:
    metadata = _json_load(_row_get(row, "metadata"), {})
    owner_identity = _owner_identity_from_row(row)
    return {
        "id": _row_get(row, "session_id"),
        "session_key": _row_get(row, "session_key"),
        "source": _row_get(row, "session_source") or metadata.get("source") or _row_get(row, "session_role"),
        "session_source": _row_get(row, "session_source") or metadata.get("source") or _row_get(row, "session_role"),
        "user_id": owner_identity,
        "owner_user_id": _row_get(row, "owner_user_id"),
        "title": _row_get(row, "title"),
        "metadata": metadata,
        "settings": _json_load(_row_get(row, "settings"), {}),
        "started_at": _row_get(row, "created_at"),
        "updated_at": _row_get(row, "updated_at"),
        "ended_at": _row_get(row, "ended_at"),
        "message_count": int(metadata.get("message_count") or 0),
        "history_version": int(_row_get(row, "history_version") or 0),
        "running_task_run_id": _row_get(row, "running_task_run_id"),
        "workspace_key": _row_get(row, "workspace_key"),
        "archived_at": _row_get(row, "archived_at"),
        "deleted_at": _row_get(row, "deleted_at"),
        "deleted_by": _row_get(row, "deleted_by"),
        "purge_after": _row_get(row, "purge_after"),
    }


def _call_session_mutation(func, **kwargs):
    try:
        return func(**kwargs)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail="forbidden") from error
    except KeyError as error:
        raise HTTPException(status_code=404, detail="session not found") from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


def _patch_public_session_metadata(store, *, owner_key: str, session_id: str, metadata_patch: dict[str, Any]) -> None:
    if hasattr(store, "connection_factory"):
        connection = store.connection_factory()
        owner_sql, owner_params = _owner_filter(owner_key)
        row = connection.execute(
            f"SELECT metadata, history_version FROM agent_sessions WHERE session_id = %s AND {owner_sql} AND deleted_at IS NULL FOR UPDATE",
            tuple([session_id, *owner_params]),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="session not found")
        metadata = _json_load(_row_get(row, "metadata"), {})
        metadata.update(metadata_patch)
        next_version = int(_row_get(row, "history_version") or 0) + 1
        connection.execute(
            f"""
            UPDATE agent_sessions
            SET metadata = %s::jsonb,
                history_version = %s,
                updated_at = now()
            WHERE session_id = %s AND {owner_sql} AND deleted_at IS NULL
            """,
            tuple([json.dumps(metadata, ensure_ascii=False, sort_keys=True), next_version, session_id, *owner_params]),
        )
        connection.commit()
        return
    session = store.sessions.get(session_id)
    if session is None or str(session.get("user_id") or "") != str(owner_key):
        raise HTTPException(status_code=404, detail="session not found")
    session["metadata"] = {**dict(session.get("metadata") or {}), **metadata_patch}
    session["history_version"] = int(session.get("history_version") or 0) + 1
    session["updated_at"] = utc_now()


def _validate_metadata_patch(metadata_patch: dict[str, Any]) -> None:
    if _PROTECTED_SESSION_METADATA_KEYS.intersection(metadata_patch):
        raise HTTPException(status_code=400, detail="metadataPatch contains protected fields")
    if set(metadata_patch) - _SESSION_METADATA_PATCH_ALLOWLIST:
        raise HTTPException(status_code=400, detail="metadataPatch contains unsupported fields")


def _replay_http_session_command(
    request: Request,
    *,
    owner_key: str,
    session_id: str,
    command_id: str | None,
    signature: str,
) -> dict[str, Any] | None:
    if not command_id:
        return None
    if hasattr(request.app.state.session_store, "get_session_command_receipt"):
        receipt = request.app.state.session_store.get_session_command_receipt(
            owner_key=owner_key,
            session_id=session_id,
            client_command_id=command_id,
        )
        if receipt is not None:
            if receipt.get("command_signature") != signature:
                raise HTTPException(status_code=409, detail="clientCommandId was already used with a different payload")
            payload = dict(receipt.get("response_payload") or {})
            if isinstance(payload.get("_http_session"), dict):
                return dict(payload["_http_session"])
            if isinstance(payload.get("session"), dict):
                return dict(payload["session"])
            return payload
    cache: dict[tuple[str, str, str], tuple[str, dict[str, Any]]] = getattr(request.app.state, "session_command_replay_cache", {})
    request.app.state.session_command_replay_cache = cache
    existing = cache.get((owner_key, session_id, command_id))
    if existing is None:
        return None
    existing_signature, session = existing
    if existing_signature != signature:
        raise HTTPException(status_code=409, detail="clientCommandId was already used with a different payload")
    return dict(session)


def _remember_http_session_command(
    request: Request,
    *,
    owner_key: str,
    session_id: str,
    command_id: str | None,
    signature: str,
    session: dict[str, Any],
) -> None:
    if not command_id:
        return
    if hasattr(request.app.state.session_store, "remember_session_command_receipt"):
        request.app.state.session_store.remember_session_command_receipt(
            owner_key=owner_key,
            session_id=session_id,
            client_command_id=command_id,
            command_signature=signature,
            response_payload={"_http_session": _jsonable(session)},
        )
    cache: dict[tuple[str, str, str], tuple[str, dict[str, Any]]] = getattr(request.app.state, "session_command_replay_cache", {})
    request.app.state.session_command_replay_cache = cache
    cache[(owner_key, session_id, command_id)] = (signature, _jsonable(session))


def _session_command_signature(operation: str, payload: dict[str, Any]) -> str:
    return json.dumps({"operation": operation, "payload": payload}, ensure_ascii=False, sort_keys=True, default=str)


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=False)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _normalize_session_settings(settings: dict[str, Any]) -> dict[str, Any]:
    if set(settings) - _SESSION_SETTINGS_ALLOWLIST:
        raise HTTPException(status_code=400, detail="settings contains unsupported fields")
    normalized: dict[str, Any] = {}
    model = settings.get("model")
    if model is not None:
        if not isinstance(model, str) or not model.strip():
            raise HTTPException(status_code=400, detail="settings.model must be a non-empty string")
        normalized["model"] = model.strip()
    system_prompt = settings.get("systemPrompt", settings.get("system_prompt"))
    if system_prompt is not None:
        if not isinstance(system_prompt, str):
            raise HTTPException(status_code=400, detail="settings.systemPrompt must be a string")
        normalized["systemPrompt"] = system_prompt
    toolsets = settings.get("toolsets")
    if toolsets is not None:
        if not isinstance(toolsets, list) or any(not isinstance(item, str) or not item.strip() for item in toolsets):
            raise HTTPException(status_code=400, detail="settings.toolsets must be a string array")
        normalized_toolsets = [item.strip() for item in toolsets]
        if any(item not in _PUBLIC_SESSION_TOOLSETS for item in normalized_toolsets):
            raise HTTPException(status_code=400, detail="settings.toolsets contains unsupported toolsets")
        normalized["toolsets"] = normalized_toolsets
    delegation_policy = settings.get("delegationPolicy", settings.get("delegation_policy"))
    if delegation_policy is not None:
        if not isinstance(delegation_policy, dict):
            raise HTTPException(status_code=400, detail="settings.delegationPolicy must be an object")
        normalized["delegationPolicy"] = _normalize_delegation_policy(delegation_policy)
    return normalized


def _normalize_delegation_policy(policy: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = {"canDelegate", "maxWorkerDepth"}
    if set(policy) - allowed_keys:
        raise HTTPException(status_code=400, detail="settings.delegationPolicy contains unsupported fields")
    can_delegate = policy.get("canDelegate", False)
    if not isinstance(can_delegate, bool):
        raise HTTPException(status_code=400, detail="settings.delegationPolicy.canDelegate must be a boolean")
    max_worker_depth = policy.get("maxWorkerDepth", 0)
    if not isinstance(max_worker_depth, int) or max_worker_depth < 0 or max_worker_depth > 1:
        raise HTTPException(status_code=400, detail="settings.delegationPolicy.maxWorkerDepth must be 0 or 1")
    return {"canDelegate": can_delegate, "maxWorkerDepth": max_worker_depth}


def _session_settings_snapshot(session: dict[str, Any]) -> dict[str, Any]:
    settings = session.get("settings")
    return dict(settings) if isinstance(settings, dict) else {}


def _apply_session_settings_snapshot(task_input: dict[str, Any], settings: dict[str, Any], *, session: dict[str, Any]) -> None:
    """세션별 설정을 생성 시점 TaskRun payload에 복사해 실행 재현성을 유지한다."""

    snapshot = dict(settings)
    task_input["settings_snapshot"] = snapshot
    if "model" in snapshot:
        task_input["model"] = snapshot["model"]
    if "toolsets" in snapshot:
        task_input["toolsets"] = list(snapshot["toolsets"])
        task_input["enabled_toolsets"] = list(snapshot["toolsets"])
    if "delegationPolicy" in snapshot:
        task_input["delegation_policy"] = dict(snapshot["delegationPolicy"])
    task_input["system_prompt_snapshot"] = get_system_prompt_snapshot(session)


def _row_get(row: Any, key: str) -> Any:
    if row is None:
        return None
    if hasattr(row, "get"):
        return row.get(key)
    try:
        return row[key]
    except (KeyError, TypeError):
        return None


def _owner_identity_from_row(row: Any) -> str | None:
    """HTTP 경계에서도 metadata.user_id를 권한 기준으로 쓰지 않는다.

    공개 세션 권한은 backend token으로 검증된 userId와 DB의 owner_user_id/FK
    또는 전환기 owner_key만 비교한다. JSON metadata는 표시/호환 영역이라
    소유권을 바꾸는 입력으로 취급하지 않는다.
    """

    owner_user_id = _row_get(row, "owner_user_id")
    if owner_user_id is not None:
        return str(owner_user_id)
    owner_key = _row_get(row, "owner_key")
    return str(owner_key) if owner_key is not None else None


def _owner_filter(owner_key: str) -> tuple[str, list[Any]]:
    owner_user_id = _owner_user_id(owner_key)
    if owner_user_id is None:
        return "owner_key = %s", [owner_key]
    return "owner_user_id = %s", [owner_user_id]


def _owner_user_id(value: Any) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _json_load(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, str):
        return json.loads(value)
    return value
