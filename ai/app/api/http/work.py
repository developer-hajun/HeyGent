from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from app.api.deps.http_auth import authenticate_http_user, ensure_owner
from app.api.deps.openapi_auth import document_bearer_auth
from app.contracts.work import (
    CreateWorkCommentRequest,
    CreateWorkRequest,
    MoveWorkStatusRequest,
    SetWorkLabelsRequest,
    UpdateWorkAssigneeRequest,
    UpdateWorkFieldsRequest,
    WorkCommentResponse,
    WorkCommentsResponse,
    WorkContextPreviewResponse,
    WorkCreateResponse,
    WorkItemResponse,
    WorkListResponse,
    WorkRunResponse,
    WorkRunsResponse,
)
from app.contracts.session import CreateSessionMessageRequest
from app.api.http.sessions import _create_message_in_session
from app.domain.work import WorkItem, WorkService
from app.domain.work.policies import normalize_disposition_status

router = APIRouter(tags=["work"], dependencies=[Depends(document_bearer_auth)])


@router.get(
    "/sessions/{sessionId}/work",
    response_model=WorkListResponse,
    summary="세션 작업 목록 조회",
)
async def list_session_work(
    request: Request,
    sessionId: str = Path(..., description="작업을 조회할 AI 세션 ID입니다."),
    status: str | None = Query(default=None, description="작업 상태 필터입니다."),
    includeArchived: bool = Query(default=False, description="보관된 작업까지 포함할지 여부입니다."),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> WorkListResponse:
    user = await authenticate_http_user(request)
    session = _session_or_404(request, sessionId)
    ensure_owner(user, session.get("user_id"))
    repository = request.app.state.work_repository
    items = repository.list_work(
        session_id=sessionId,
        owner_key=str(user.user_id),
        status=status,
        include_archived=includeArchived,
        limit=limit,
        offset=offset,
    )
    return WorkListResponse(items=[_work_response(item) for item in items], totalCount=len(items))


@router.post(
    "/sessions/{sessionId}/work",
    response_model=WorkCreateResponse,
    summary="작업 모드 새 작업 생성과 실행 시작",
)
async def create_session_work(
    request: Request,
    payload: CreateWorkRequest,
    sessionId: str = Path(..., description="작업을 생성할 AI 세션 ID입니다."),
) -> WorkCreateResponse:
    user = await authenticate_http_user(request)
    session = _session_or_404(request, sessionId)
    ensure_owner(user, session.get("user_id"))

    service = WorkService(request.app.state.work_repository)
    work = service.create_from_payload(
        session_id=sessionId,
        owner_key=str(user.user_id),
        owner_user_id=_int_or_none(user.user_id),
        payload=payload.model_dump(by_alias=True),
        client_request_id=payload.client_request_id,
    )
    if payload.initial_comment:
        service.add_comment(
            work=work,
            body=payload.initial_comment,
            author_type="user",
            author_id=str(user.user_id),
        )
    if not payload.start_execution:
        await _publish_work_event(request, str(user.user_id), "work.created", work=work)
        return WorkCreateResponse(work=_work_response(work), taskRunId=None, taskStatus=None)

    task_status: str | None = None
    task_run_id: str | None = None
    try:
        message = await _create_message_in_session(
            request,
            CreateSessionMessageRequest(
                content=work.execution_instruction or work.description or work.title,
                clientMessageId=payload.client_request_id,
                inputPayload={"workId": work.work_id},
            ),
            session=session,
            user=user,
        )
        task_run_id = message.task_run_id
        task_status = message.status
    except Exception as error:
        updated = service.mark_run_start_failed(work_id=work.work_id, reason=str(error))
        await _publish_work_event(request, str(user.user_id), "work.updated", work=updated)
        return WorkCreateResponse(work=_work_response(updated), taskRunId=None, taskStatus="FAILED_TO_START")
    updated = request.app.state.work_repository.get_work(work.work_id) or work
    await _publish_work_event(request, str(user.user_id), "work.created", work=updated)
    return WorkCreateResponse(work=_work_response(updated), taskRunId=task_run_id, taskStatus=task_status)


@router.get("/work/{workId}", response_model=WorkItemResponse, summary="작업 상세 조회")
async def get_work(request: Request, workId: str = Path(...)) -> WorkItemResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    return _work_response(work)


@router.post("/work/{workId}/move-status", response_model=WorkItemResponse, summary="작업 상태 변경")
async def move_work_status(request: Request, payload: MoveWorkStatusRequest, workId: str = Path(...)) -> WorkItemResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    status = normalize_disposition_status(payload.status)
    if status is None:
        raise HTTPException(status_code=400, detail="invalid work status")
    updated = request.app.state.work_repository.update_status(workId, status)
    await _publish_work_event(request, str(user.user_id), "work.updated", work=updated)
    return _work_response(updated)


@router.post("/work/{workId}/update-fields", response_model=WorkItemResponse, summary="작업 제목과 설명 변경")
async def update_work_fields(request: Request, payload: UpdateWorkFieldsRequest, workId: str = Path(...)) -> WorkItemResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    title = payload.title.strip() if payload.title is not None else None
    description = payload.description.strip() if payload.description is not None else None
    updated = request.app.state.work_repository.update_fields(workId, title=title, description=description)
    await _publish_work_event(request, str(user.user_id), "work.updated", work=updated)
    return _work_response(updated)


@router.post("/work/{workId}/assign", response_model=WorkItemResponse, summary="작업 담당 에이전트 변경")
async def update_work_assignee(request: Request, payload: UpdateWorkAssigneeRequest, workId: str = Path(...)) -> WorkItemResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    assignee_agent_id = payload.assignee_agent_id.strip() if payload.assignee_agent_id else None
    updated = request.app.state.work_repository.update_assignee(workId, assignee_agent_id=assignee_agent_id)
    await _publish_work_event(request, str(user.user_id), "work.updated", work=updated)
    return _work_response(updated)


@router.post("/work/{workId}/archive", response_model=WorkItemResponse, summary="작업 보관")
async def archive_work(request: Request, workId: str = Path(...)) -> WorkItemResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    updated = request.app.state.work_repository.archive_work(workId)
    await _publish_work_event(request, str(user.user_id), "work.updated", work=updated)
    return _work_response(updated)


@router.post("/work/{workId}/restore", response_model=WorkItemResponse, summary="작업 복구")
async def restore_work(request: Request, workId: str = Path(...)) -> WorkItemResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    updated = request.app.state.work_repository.restore_work(workId)
    await _publish_work_event(request, str(user.user_id), "work.updated", work=updated)
    return _work_response(updated)


@router.post("/work/{workId}/set-labels", response_model=WorkItemResponse, summary="작업 라벨 교체")
async def set_work_labels(request: Request, payload: SetWorkLabelsRequest, workId: str = Path(...)) -> WorkItemResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    request.app.state.work_repository.set_label_links_by_names(
        workId,
        session_id=work.session_id,
        owner_key=work.owner_key,
        label_names=payload.label_names,
    )
    updated = _work_or_404(request, workId)
    await _publish_work_event(request, str(user.user_id), "work.updated", work=updated)
    return _work_response(updated)


@router.get("/work/{workId}/comments", response_model=WorkCommentsResponse, summary="작업 댓글 목록")
async def list_work_comments(
    request: Request,
    workId: str = Path(...),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> WorkCommentsResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    items = request.app.state.work_repository.list_comments(workId, limit=limit, offset=offset)
    return WorkCommentsResponse(items=[_comment_response(item) for item in items], totalCount=len(items))


@router.post("/work/{workId}/comments", response_model=WorkCommentResponse, summary="작업 댓글 추가")
async def add_work_comment(request: Request, payload: CreateWorkCommentRequest, workId: str = Path(...)) -> WorkCommentResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    comment = WorkService(request.app.state.work_repository).add_comment(
        work=work,
        body=payload.body,
        author_type="user",
        author_id=str(user.user_id),
        resume_requested=payload.resume,
    )
    updated = _work_or_404(request, workId)
    await _publish_work_event(request, str(user.user_id), "work_comment.created", work=updated, comment=comment)
    return _comment_response(comment)


@router.get("/work/{workId}/runs", response_model=WorkRunsResponse, summary="작업 실행 이력")
async def list_work_runs(
    request: Request,
    workId: str = Path(...),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> WorkRunsResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    items = request.app.state.work_repository.list_runs(workId, limit=limit, offset=offset)
    return WorkRunsResponse(items=[_run_response(item) for item in items], totalCount=len(items))


@router.get("/work/{workId}/context-preview", response_model=WorkContextPreviewResponse, summary="디버깅용 작업 컨텍스트 조회")
async def get_work_context_preview(request: Request, workId: str = Path(...)) -> WorkContextPreviewResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    return WorkContextPreviewResponse(**request.app.state.work_repository.context_preview(workId))


def _session_or_404(request: Request, session_id: str) -> dict[str, Any]:
    session = request.app.state.session_store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return session


def _work_or_404(request: Request, work_id: str) -> WorkItem:
    work = request.app.state.work_repository.get_work(work_id)
    if work is None:
        raise HTTPException(status_code=404, detail="work not found")
    return work


def _ensure_work_owner(user, work: WorkItem) -> None:
    ensure_owner(user, work.owner_key)


def _work_response(work: WorkItem) -> WorkItemResponse:
    return WorkItemResponse.model_validate(work, from_attributes=True)


def _comment_response(comment) -> WorkCommentResponse:
    return WorkCommentResponse.model_validate(comment, from_attributes=True)


def _run_response(run) -> WorkRunResponse:
    return WorkRunResponse.model_validate(run, from_attributes=True)


def _int_or_none(value: Any) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


async def _publish_work_event(
    request: Request,
    owner_key: str,
    event_type: str,
    *,
    work: WorkItem,
    comment=None,
) -> None:
    manager = getattr(request.app.state, "ws_manager", None)
    if manager is None:
        return
    payload: dict[str, Any] = {
        "work": _work_response(work).model_dump(mode="json", by_alias=True),
    }
    if comment is not None:
        payload["comment"] = _comment_response(comment).model_dump(mode="json", by_alias=True)
    await manager.broadcast(
        {"protocolVersion": 1, "type": event_type, "payload": payload},
        f"work:{owner_key}",
    )
