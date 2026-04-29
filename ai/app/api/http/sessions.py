from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from app.api.deps.http_auth import authenticate_http_user, ensure_owner
from app.api.deps.openapi_auth import document_bearer_auth
from app.contracts.session import (
    CreateSessionMessageRequest,
    CreateSessionMessageResponse,
    SessionListResponse,
    SessionMessageResponse,
    SessionMessagesResponse,
    SessionResponse,
)
from app.core.utils.ids import new_id
from app.domain.orchestration.contracts import OrchestrationRequest

router = APIRouter(prefix="/sessions", tags=["sessions"], dependencies=[Depends(document_bearer_auth)])

_PUBLIC_SESSION_SOURCE = "api.session"
_TASK_TRANSCRIPT_SOURCE = "agent.loop"


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
) -> SessionListResponse:
    user = await authenticate_http_user(request)
    offset = (page - 1) * page_size
    items, total_count = _list_public_sessions(
        request.app.state.session_store,
        owner_key=user.user_id,
        limit=page_size,
        offset=offset,
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

    user_message_id = session_store.append_message(
        session_id=sessionId,
        role="user",
        content=payload.content,
        metadata={"source": _PUBLIC_SESSION_SOURCE},
    )
    task_transcript_session_id = _create_task_transcript_session(
        session_store,
        session_id=sessionId,
        owner_key=owner_key,
        title=session.get("title") or payload.content[:120],
        model=payload.model,
    )
    task_input = dict(payload.input_payload)
    if payload.model and not task_input.get("model"):
        task_input["model"] = payload.model
    task_input["prompt"] = payload.content
    task_input["transcript_session_id"] = task_transcript_session_id

    try:
        task = await request.app.state.orchestrator.start(
            OrchestrationRequest(
                owner_key=owner_key,
                session_key=sessionId,
                input_payload=task_input,
                intent_type=payload.intent_type,
            )
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"unknown intent or handler: {error.args[0]}") from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    assistant_content = _assistant_content_from_task(task)
    assistant_message_id = session_store.append_message(
        session_id=sessionId,
        role="assistant",
        content=assistant_content,
        metadata={
            "source": _PUBLIC_SESSION_SOURCE,
            "task_run_id": task.task_run_id,
            "status": task.status,
        },
        finish_reason="stop" if task.status == "COMPLETED" else None,
    )
    messages_by_id = {message["id"]: message for message in session_store.list_messages(sessionId)}
    return CreateSessionMessageResponse(
        session_id=sessionId,
        task_run_id=task.task_run_id,
        status=task.status,
        user_message=_message_response(messages_by_id[user_message_id]),
        assistant_message=_message_response(messages_by_id[assistant_message_id]),
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


def _get_public_session_or_404(request: Request, session_id: str) -> dict[str, Any]:
    session = request.app.state.session_store.get_session(session_id)
    if session is None or not _is_public_session(session):
        raise HTTPException(status_code=404, detail="session not found")
    return session


def _is_public_session(session: dict[str, Any]) -> bool:
    metadata = dict(session.get("metadata") or {})
    return session.get("source") == _PUBLIC_SESSION_SOURCE or metadata.get("source") == _PUBLIC_SESSION_SOURCE


def _session_response(session: dict[str, Any]) -> SessionResponse:
    metadata = dict(session.get("metadata") or {})
    metadata.pop("source", None)
    return SessionResponse(
        session_id=str(session["id"]),
        title=session.get("title"),
        owner_key=session.get("user_id"),
        status=session.get("status"),
        source=session.get("source"),
        parent_session_id=session.get("parent_session_id"),
        message_count=int(session.get("message_count") or 0),
        created_at=session.get("started_at"),
        updated_at=session.get("updated_at"),
        ended_at=session.get("ended_at"),
        metadata=metadata,
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


def _list_public_sessions(store, *, owner_key: str | None, limit: int, offset: int) -> tuple[list[dict[str, Any]], int]:
    if hasattr(store, "connection_factory"):
        return _list_postgres_public_sessions(store, owner_key=owner_key, limit=limit, offset=offset)
    return [], 0


def _list_postgres_public_sessions(store, *, owner_key: str | None, limit: int, offset: int) -> tuple[list[dict[str, Any]], int]:
    where = ["metadata->>'source' = %s"]
    params: list[Any] = [_PUBLIC_SESSION_SOURCE]
    if owner_key is not None:
        where.append("owner_key = %s")
        params.append(owner_key)
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
    return {
        "id": _row_get(row, "session_id"),
        "session_key": _row_get(row, "session_key"),
        "source": metadata.get("source") or _row_get(row, "session_role"),
        "user_id": metadata.get("user_id") or _row_get(row, "owner_key"),
        "title": _row_get(row, "title"),
        "metadata": metadata,
        "started_at": _row_get(row, "created_at"),
        "updated_at": _row_get(row, "updated_at"),
        "ended_at": _row_get(row, "ended_at"),
        "message_count": int(metadata.get("message_count") or 0),
    }


def _row_get(row: Any, key: str) -> Any:
    if row is None:
        return None
    if hasattr(row, "get"):
        return row.get(key)
    try:
        return row[key]
    except (KeyError, TypeError):
        return None


def _json_load(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, str):
        return json.loads(value)
    return value
