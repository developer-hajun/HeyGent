from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from app.api.deps.http_auth import authenticate_http_user, ensure_owner
from app.api.deps.openapi_auth import document_bearer_auth
from app.contracts.work import (
    CreateWorkLabelRequest,
    CreateWorkCommentRequest,
    CreateChildWorkRequest,
    CreateWorkInteractionRequest,
    CreateWorkProductRequest,
    CreateWorkRunRequest,
    CreateWorkRequest,
    MoveWorkStatusRequest,
    RespondWorkInteractionRequest,
    SetWorkLabelsRequest,
    UpdateWorkParentRequest,
    UpdateWorkLabelRequest,
    UpdateWorkAssigneeRequest,
    UpdateWorkFieldsRequest,
    UpdateWorkFlowOrderRequest,
    UpdateWorkProductRequest,
    UpsertWorkDocumentRequest,
    UpsertWorkRelationRequest,
    WorkCommentResponse,
    WorkCommentsResponse,
    WorkContextPreviewResponse,
    WorkCreateResponse,
    WorkDocumentResponse,
    WorkDocumentRevisionResponse,
    WorkDocumentRevisionsResponse,
    WorkDocumentsResponse,
    WorkInteractionResponse,
    WorkInteractionsResponse,
    WorkItemResponse,
    WorkFlowResponse,
    WorkLabelResponse,
    WorkLabelsResponse,
    WorkListResponse,
    WorkProductResponse,
    WorkProductsResponse,
    WorkRecoveryActionResponse,
    WorkRecoveryActionsResponse,
    WorkRelationResponse,
    WorkRelationsResponse,
    WorkRunResponse,
    WorkRunsResponse,
    WorkWakeResponse,
    WorkWakesResponse,
)
from app.contracts.session import CreateSessionMessageRequest
from app.core.utils.ids import new_id
from app.domain.providers.model.base import AgentMessage
from app.api.http.sessions import (
    _create_message_in_session,
    enqueue_parent_wakes_after_child_terminal,
    enqueue_unblocked_target_wakes,
    enqueue_work_graph_wake,
)
from app.domain.work import WorkComment, WorkItem, WorkService
from app.domain.work.models import WorkWakeRequest
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
    return WorkListResponse(items=[_work_response(item, repository=repository) for item in items], totalCount=len(items))


@router.post(
    "/sessions/{sessionId}/work/flow-order",
    response_model=WorkListResponse,
    summary="세션 작업 구조도 표시 순서 변경",
)
async def update_session_work_flow_order(
    request: Request,
    payload: UpdateWorkFlowOrderRequest,
    sessionId: str = Path(..., description="구조도 순서를 저장할 AI 세션 ID입니다."),
) -> WorkListResponse:
    user = await authenticate_http_user(request)
    session = _session_or_404(request, sessionId)
    ensure_owner(user, session.get("user_id"))
    repository = request.app.state.work_repository
    requested_ids = [work_id.strip() for work_id in payload.work_ids if work_id.strip()]
    if len(requested_ids) != len(set(requested_ids)):
        raise HTTPException(status_code=400, detail="duplicate work ids are not allowed")
    current_items = [
        item
        for item in repository.list_work(
            session_id=sessionId,
            owner_key=str(user.user_id),
            include_archived=True,
            limit=500,
            offset=0,
        )
        if item.parent_id is None
    ]
    current_ids = {item.work_id for item in current_items}
    if set(requested_ids) != current_ids:
        raise HTTPException(status_code=400, detail="flow order must include every root work")
    updated_items = repository.update_root_flow_order(
        session_id=sessionId,
        owner_key=str(user.user_id),
        work_ids=requested_ids,
    )
    for item in updated_items:
        await _publish_work_event(request, str(user.user_id), "work.updated", work=item)
    return WorkListResponse(items=[_work_response(item, repository=repository) for item in updated_items], totalCount=len(updated_items))


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
    work_payload = payload.model_dump(by_alias=True)
    work_payload = await _enrich_work_payload(request, session=session, payload=work_payload)
    _validate_assignee_or_400(request, session_id=sessionId, owner_key=str(user.user_id), assignee_agent_id=work_payload.get("assigneeAgentId"))
    work = service.create_from_payload(
        session_id=sessionId,
        owner_key=str(user.user_id),
        owner_user_id=_int_or_none(user.user_id),
        payload=work_payload,
        client_request_id=payload.client_request_id,
    )
    if not payload.start_execution:
        work = request.app.state.work_repository.update_status(work.work_id, "todo")
    if payload.initial_comment:
        service.add_comment(
            work=work,
            body=payload.initial_comment,
            author_type="user",
            author_id=str(user.user_id),
        )
    if not payload.start_execution:
        await _publish_work_event(request, str(user.user_id), "work.created", work=work)
        return WorkCreateResponse(work=_work_response(work, repository=request.app.state.work_repository), taskRunId=None, taskStatus=None)

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
        return WorkCreateResponse(work=_work_response(updated, repository=request.app.state.work_repository), taskRunId=None, taskStatus="FAILED_TO_START")
    updated = request.app.state.work_repository.get_work(work.work_id) or work
    await _publish_work_event(request, str(user.user_id), "work.created", work=updated)
    return WorkCreateResponse(work=_work_response(updated, repository=request.app.state.work_repository), taskRunId=task_run_id, taskStatus=task_status)


async def _enrich_work_payload(request: Request, *, session: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    raw_user_input = str(payload.get("rawUserInput") or payload.get("raw_user_input") or "").strip()
    current_title = str(payload.get("title") or "").strip()
    if not raw_user_input:
        return payload
    generated_payload = await _generate_work_payload(request, session=session, raw_user_input=raw_user_input)
    enriched = {**payload, **generated_payload}
    if current_title and not _should_generate_work_title(current_title=current_title, raw_user_input=raw_user_input):
        enriched["title"] = current_title
    else:
        enriched["title"] = str(generated_payload.get("title") or "").strip() or await _generate_work_title(request, session=session, raw_user_input=raw_user_input) or _fallback_work_title(raw_user_input)
    enriched["rawUserInput"] = raw_user_input
    enriched.setdefault("description", raw_user_input)
    enriched.setdefault("executionInstruction", raw_user_input)
    return enriched


async def _enrich_work_payload_title(request: Request, *, session: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    return await _enrich_work_payload(request, session=session, payload=payload)


async def _generate_work_payload(request: Request, *, session: dict[str, Any], raw_user_input: str) -> dict[str, Any]:
    registry = getattr(request.app.state, "provider_registry", None)
    if registry is None:
        return {}
    try:
        provider = registry.preferred_model_provider()
    except Exception:
        return {}
    model = _work_title_model(request, session=session)
    messages = [
        AgentMessage(
            role="system",
            content=(
                "사용자 입력을 작업 생성 payload로 구조화한다. JSON 객체만 반환한다. "
                "필드: title, description, executionInstruction, expectedDeliverable, "
                "acceptanceCriteria, constraints, labelNames, initialComment, metadata. "
                "title은 한국어 명사구 4~12단어, description과 executionInstruction은 원문 의미를 보존한다. "
                "확실하지 않은 배열 필드는 빈 배열로 둔다."
            ),
        ),
        AgentMessage(role="user", content=raw_user_input[:4000]),
    ]
    try:
        response = await asyncio.wait_for(_respond_provider_async(provider, messages=messages, tools=[], model=model), timeout=10)
    except Exception:
        return {}
    return _sanitize_generated_work_payload(response.output_text)


def _should_generate_work_title(*, current_title: str, raw_user_input: str) -> bool:
    if not current_title:
        return True
    normalized_title = _normalize_title_text(current_title)
    normalized_raw = _normalize_title_text(raw_user_input)
    first_line = _normalize_title_text(raw_user_input.splitlines()[0] if raw_user_input.splitlines() else raw_user_input)
    return (
        len(current_title) > 48
        or normalized_title == normalized_raw
        or normalized_title == first_line
        or _contains_local_path(current_title)
    )


async def _generate_work_title(request: Request, *, session: dict[str, Any], raw_user_input: str) -> str | None:
    registry = getattr(request.app.state, "provider_registry", None)
    if registry is None:
        return None
    try:
        provider = registry.preferred_model_provider()
    except Exception:
        return None
    model = _work_title_model(request, session=session)
    messages = [
        AgentMessage(
            role="system",
            content=(
                "사용자 입력을 작업 보드 제목으로 요약한다. "
                "한국어 명사구로 4~12단어만 반환하고, 마크다운/따옴표/문장부호/파일 경로는 쓰지 않는다."
            ),
        ),
        AgentMessage(role="user", content=raw_user_input[:4000]),
    ]
    try:
        response = await asyncio.wait_for(_respond_provider_async(provider, messages=messages, tools=[], model=model), timeout=8)
    except Exception:
        return None
    return _sanitize_generated_work_title(response.output_text)


def _work_title_model(request: Request, *, session: dict[str, Any]) -> str:
    settings_snapshot = dict(session.get("settings") or {})
    return str(settings_snapshot.get("model") or getattr(request.app.state.settings, "openai_response_model", "") or "gpt-5.4-mini")


async def _respond_provider_async(provider, **kwargs):
    respond_async = getattr(provider, "respond_async", None)
    if callable(respond_async):
        return await respond_async(**kwargs)
    return await asyncio.to_thread(provider.respond, **kwargs)


def _sanitize_generated_work_title(value: str) -> str | None:
    title = value.strip().splitlines()[0].strip()
    title = re.sub(r"^[`'\"“”‘’\s\-\*\d\.\)]+", "", title)
    title = re.sub(r"[`'\"“”‘’\s\*]+$", "", title)
    title = re.sub(r"\s+", " ", title)
    title = re.sub(r"[.。!?！？]+$", "", title).strip()
    if not title or _contains_local_path(title):
        return None
    return title[:48].rstrip()


def _sanitize_generated_work_payload(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(_extract_json_object(value))
    except Exception:
        return {}
    if not isinstance(parsed, dict):
        return {}
    result: dict[str, Any] = {}
    for key in ("title", "description", "executionInstruction", "expectedDeliverable", "initialComment"):
        text = str(parsed.get(key) or "").strip()
        if text:
            result[key] = text
    for key in ("acceptanceCriteria", "constraints", "labelNames"):
        raw_items = parsed.get(key)
        if isinstance(raw_items, list):
            result[key] = [str(item).strip() for item in raw_items if str(item).strip()]
    metadata = parsed.get("metadata")
    if isinstance(metadata, dict):
        result["metadata"] = metadata
    if "title" in result:
        result["title"] = _sanitize_generated_work_title(str(result["title"])) or str(result["title"])[:48].rstrip()
    return result


def _extract_json_object(value: str) -> str:
    text = str(value or "").strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if fenced:
        return fenced.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    return text


def _fallback_work_title(raw_user_input: str) -> str:
    cleaned = _normalize_title_text(raw_user_input)
    cleaned = re.sub(r"[A-Za-z]:\\[^\s]+", "", cleaned)
    cleaned = re.sub(r"/[^\s]+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return "새 작업"
    return cleaned[:48].rstrip()


def _normalize_title_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _contains_local_path(value: str) -> bool:
    return bool(re.search(r"[A-Za-z]:\\|/[A-Za-z0-9_.-]+/", value))


@router.get("/work/{workId}", response_model=WorkItemResponse, summary="작업 상세 조회")
async def get_work(request: Request, workId: str = Path(...)) -> WorkItemResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    return _work_response(work, repository=request.app.state.work_repository)


@router.get("/work/{workId}/flow", response_model=WorkFlowResponse, summary="작업 구조도 조회")
async def get_work_flow(request: Request, workId: str = Path(...)) -> WorkFlowResponse:
    user = await authenticate_http_user(request)
    root = _work_or_404(request, workId)
    _ensure_work_owner(user, root)
    repository = request.app.state.work_repository
    children = repository.list_children(root.work_id)
    relation_by_key = {}
    for work in [root, *children]:
        for relation in _safe_relations(repository, work.work_id):
            relation_by_key[(relation.source_work_id, relation.target_work_id, relation.relation_type)] = relation
    return WorkFlowResponse(
        root=_work_response(root, repository=repository),
        items=[_work_response(child, repository=repository) for child in children],
        relations=[_relation_response(relation) for relation in relation_by_key.values()],
    )


@router.post("/work/{workId}/move-status", response_model=WorkItemResponse, summary="작업 상태 변경")
async def move_work_status(request: Request, payload: MoveWorkStatusRequest, workId: str = Path(...)) -> WorkItemResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    status = normalize_disposition_status(payload.status)
    if status is None:
        raise HTTPException(status_code=400, detail="invalid work status")
    updated = request.app.state.work_repository.update_status(workId, status)
    if status in {"done", "cancelled"}:
        await enqueue_unblocked_target_wakes(request, user=user, work=updated)
        await enqueue_parent_wakes_after_child_terminal(request, user=user, work=updated)
    await _publish_work_event(request, str(user.user_id), "work.updated", work=updated)
    return _work_response(updated, repository=request.app.state.work_repository)


@router.post("/work/{workId}/update-fields", response_model=WorkItemResponse, summary="작업 제목과 설명 변경")
async def update_work_fields(request: Request, payload: UpdateWorkFieldsRequest, workId: str = Path(...)) -> WorkItemResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    title = payload.title.strip() if payload.title is not None else None
    description = payload.description.strip() if payload.description is not None else None
    updated = request.app.state.work_repository.update_fields(workId, title=title, description=description)
    await _publish_work_event(request, str(user.user_id), "work.updated", work=updated)
    return _work_response(updated, repository=request.app.state.work_repository)


@router.post("/work/{workId}/assign", response_model=WorkItemResponse, summary="작업 담당 에이전트 변경")
async def update_work_assignee(request: Request, payload: UpdateWorkAssigneeRequest, workId: str = Path(...)) -> WorkItemResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    assignee_agent_id = payload.assignee_agent_id.strip() if payload.assignee_agent_id else None
    _validate_assignee_or_400(request, session_id=work.session_id, owner_key=work.owner_key, assignee_agent_id=assignee_agent_id)
    updated = request.app.state.work_repository.update_assignee(workId, assignee_agent_id=assignee_agent_id)
    await _publish_work_event(request, str(user.user_id), "work.updated", work=updated)
    return _work_response(updated, repository=request.app.state.work_repository)


@router.post("/work/{workId}/update-parent", response_model=WorkItemResponse, summary="작업 부모 변경")
async def update_work_parent(request: Request, payload: UpdateWorkParentRequest, workId: str = Path(...)) -> WorkItemResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    parent_id = payload.parent_id.strip() if payload.parent_id else None
    if parent_id:
        parent = _work_or_404(request, parent_id)
        _ensure_work_owner(user, parent)
        if parent.session_id != work.session_id:
            raise HTTPException(status_code=409, detail="parent work belongs to another session")
        if parent.work_id == work.work_id or _would_create_parent_cycle(request.app.state.work_repository, work_id=work.work_id, parent_id=parent.work_id):
            raise HTTPException(status_code=409, detail="parent cycle is not allowed")
    updated = request.app.state.work_repository.update_parent(workId, parent_id=parent_id)
    if parent_id:
        request.app.state.work_repository.inherit_parent_labels(workId, parent_id)
    await _publish_work_event(request, str(user.user_id), "work.updated", work=updated)
    return _work_response(updated, repository=request.app.state.work_repository)


@router.post("/work/{workId}/flow-order", response_model=WorkListResponse, summary="작업 구조도 표시 순서 변경")
async def update_work_flow_order(request: Request, payload: UpdateWorkFlowOrderRequest, workId: str = Path(...)) -> WorkListResponse:
    user = await authenticate_http_user(request)
    parent = _work_or_404(request, workId)
    _ensure_work_owner(user, parent)
    repository = request.app.state.work_repository
    requested_ids = [work_id.strip() for work_id in payload.work_ids if work_id.strip()]
    if len(requested_ids) != len(set(requested_ids)):
        raise HTTPException(status_code=400, detail="duplicate work ids are not allowed")
    current_children = repository.list_children(parent.work_id)
    child_by_id = {child.work_id: child for child in current_children}
    if set(requested_ids) != set(child_by_id):
        raise HTTPException(status_code=400, detail="flow order must include every child work")
    updated_items = repository.update_flow_order(parent.work_id, requested_ids)
    for item in updated_items:
        await _publish_work_event(request, str(user.user_id), "work.updated", work=item)
    await _publish_work_event(request, str(user.user_id), "work.updated", work=parent)
    return WorkListResponse(items=[_work_response(item, repository=repository) for item in updated_items], totalCount=len(updated_items))


@router.post("/work/{workId}/children", response_model=WorkItemResponse, summary="하위 작업 생성")
async def create_child_work(request: Request, payload: CreateChildWorkRequest, workId: str = Path(...)) -> WorkItemResponse:
    user = await authenticate_http_user(request)
    parent = _work_or_404(request, workId)
    _ensure_work_owner(user, parent)
    assignee_agent_id = payload.assignee_agent_id.strip() if payload.assignee_agent_id else None
    _validate_assignee_or_400(request, session_id=parent.session_id, owner_key=parent.owner_key, assignee_agent_id=assignee_agent_id)
    child_payload = {
        "title": payload.title.strip(),
        "description": (payload.description or payload.title).strip(),
        "rawUserInput": (payload.description or payload.title).strip(),
        "executionInstruction": (payload.description or payload.title).strip(),
        "assigneeAgentId": assignee_agent_id or "CEO",
        "parentId": parent.work_id,
        "flowOrder": payload.flow_order,
        "acceptanceCriteria": payload.acceptance_criteria,
        "metadata": {"createdFromParent": parent.identifier},
    }
    service = WorkService(request.app.state.work_repository)
    child = service.create_from_payload(
        session_id=parent.session_id,
        owner_key=parent.owner_key,
        owner_user_id=_int_or_none(user.user_id),
        payload=child_payload,
        client_request_id=payload.client_request_id,
    )
    request.app.state.work_repository.update_status(child.work_id, "todo")
    if payload.block_parent_until_done:
        request.app.state.work_repository.add_relation(source_work_id=child.work_id, target_work_id=parent.work_id, relation_type="blocks")
    updated_child = _work_or_404(request, child.work_id)
    await _publish_work_event(request, str(user.user_id), "work.created", work=updated_child)
    await _publish_work_event(request, str(user.user_id), "work.updated", work=_work_or_404(request, parent.work_id))
    return _work_response(updated_child, repository=request.app.state.work_repository)


@router.post("/work/{workId}/archive", response_model=WorkItemResponse, summary="작업 보관")
async def archive_work(request: Request, workId: str = Path(...)) -> WorkItemResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    updated = request.app.state.work_repository.archive_work(workId)
    await _publish_work_event(request, str(user.user_id), "work.updated", work=updated)
    return _work_response(updated, repository=request.app.state.work_repository)


@router.post("/work/{workId}/restore", response_model=WorkItemResponse, summary="작업 복구")
async def restore_work(request: Request, workId: str = Path(...)) -> WorkItemResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    updated = request.app.state.work_repository.restore_work(workId)
    await _publish_work_event(request, str(user.user_id), "work.updated", work=updated)
    return _work_response(updated, repository=request.app.state.work_repository)


@router.delete("/work/{workId}", response_model=WorkItemResponse, summary="작업 삭제")
async def delete_work(
    request: Request,
    workId: str = Path(...),
    cascadeChildren: bool = Query(default=False, description="하위 작업까지 함께 삭제할지 여부입니다."),
) -> WorkItemResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    descendants = _list_descendant_works(request.app.state.work_repository, work.work_id)
    if cascadeChildren:
        for child in reversed(descendants):
            _ensure_work_owner(user, child)
            deleted_child = request.app.state.work_repository.delete_work(child.work_id)
            await _publish_work_event(request, str(user.user_id), "work.deleted", work=deleted_child)
    else:
        for child in [item for item in descendants if item.parent_id == work.work_id]:
            _ensure_work_owner(user, child)
            updated_child = request.app.state.work_repository.update_parent(child.work_id, parent_id=None)
            await _publish_work_event(request, str(user.user_id), "work.updated", work=updated_child)
    deleted = request.app.state.work_repository.delete_work(workId)
    await _publish_work_event(request, str(user.user_id), "work.deleted", work=deleted)
    return _work_response(deleted, repository=request.app.state.work_repository)


@router.post("/work/{workId}/set-labels", response_model=WorkItemResponse, summary="작업 라벨 교체")
async def set_work_labels(request: Request, payload: SetWorkLabelsRequest, workId: str = Path(...)) -> WorkItemResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    if payload.label_ids:
        request.app.state.work_repository.set_label_links_by_ids(workId, session_id=work.session_id, owner_key=work.owner_key, label_ids=payload.label_ids)
    else:
        request.app.state.work_repository.set_label_links_by_names(workId, session_id=work.session_id, owner_key=work.owner_key, label_names=payload.label_names)
    updated = _work_or_404(request, workId)
    await _publish_work_event(request, str(user.user_id), "work.updated", work=updated)
    return _work_response(updated, repository=request.app.state.work_repository)


@router.get("/sessions/{sessionId}/work-labels", response_model=WorkLabelsResponse, summary="세션 작업 라벨 목록")
async def list_work_labels(request: Request, sessionId: str = Path(...)) -> WorkLabelsResponse:
    user = await authenticate_http_user(request)
    session = _session_or_404(request, sessionId)
    ensure_owner(user, session.get("user_id"))
    labels = request.app.state.work_repository.list_labels(sessionId, owner_key=str(user.user_id))
    return WorkLabelsResponse(items=[_label_response(label) for label in labels], totalCount=len(labels))


@router.post("/sessions/{sessionId}/work-labels", response_model=WorkLabelResponse, summary="작업 라벨 생성")
async def create_work_label(request: Request, payload: CreateWorkLabelRequest, sessionId: str = Path(...)) -> WorkLabelResponse:
    user = await authenticate_http_user(request)
    session = _session_or_404(request, sessionId)
    ensure_owner(user, session.get("user_id"))
    label = request.app.state.work_repository.create_label(session_id=sessionId, owner_key=str(user.user_id), name=payload.name.strip(), color=_label_color(payload.color))
    await _publish_label_event(request, str(user.user_id), "work_label.created", label=label)
    return _label_response(label)


@router.post("/work-labels/{labelId}/update-fields", response_model=WorkLabelResponse, summary="작업 라벨 수정")
async def update_work_label(request: Request, payload: UpdateWorkLabelRequest, labelId: str = Path(...)) -> WorkLabelResponse:
    user = await authenticate_http_user(request)
    existing = request.app.state.work_repository.get_label(labelId)
    if existing is None or str(existing.owner_key) != str(user.user_id):
        raise HTTPException(status_code=404, detail="work label not found")
    label = request.app.state.work_repository.update_label(labelId, name=payload.name.strip() if payload.name is not None else None, color=_label_color(payload.color) if payload.color is not None else None)
    await _publish_label_event(request, str(user.user_id), "work_label.updated", label=label)
    return _label_response(label)


@router.delete("/work-labels/{labelId}", response_model=dict, summary="작업 라벨 삭제")
async def delete_work_label(request: Request, labelId: str = Path(...)) -> dict[str, bool]:
    user = await authenticate_http_user(request)
    existing = request.app.state.work_repository.get_label(labelId)
    if existing is None or str(existing.owner_key) != str(user.user_id):
        raise HTTPException(status_code=404, detail="work label not found")
    deleted = request.app.state.work_repository.delete_label(labelId)
    await _publish_simple_event(request, str(user.user_id), "work_label.deleted", {"labelId": labelId})
    return {"deleted": deleted}


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
    unresolved_blocker_ids = _unresolved_blocker_work_ids(request.app.state.work_repository, work.work_id)
    resume_requested = _effective_comment_resume_requested(
        work=work,
        payload_resume=payload.resume,
        unresolved_blocker_ids=unresolved_blocker_ids,
    )
    comment = WorkService(request.app.state.work_repository).add_comment(
        work=work,
        body=payload.body,
        author_type="user",
        author_id=str(user.user_id),
        resume_requested=resume_requested,
    )
    updated = _work_or_404(request, workId)
    if _should_reopen_blocked_work_from_comment(work=updated, unresolved_blocker_ids=unresolved_blocker_ids):
        updated = request.app.state.work_repository.update_status(work.work_id, "todo")
    await _publish_work_event(request, str(user.user_id), "work_comment.created", work=updated, comment=comment)
    await _wake_work_from_comment(request, user=user, work=updated, comment=comment)
    return _comment_response(comment)


@router.delete("/work/{workId}/comments/{commentId}", response_model=dict, summary="작업 댓글 삭제")
async def delete_work_comment(request: Request, workId: str = Path(...), commentId: str = Path(...)) -> dict[str, bool]:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    deleted = request.app.state.work_repository.delete_comment(workId, commentId)
    if not deleted:
        raise HTTPException(status_code=404, detail="work comment not found")
    await _publish_work_event(request, str(user.user_id), "work_comment.deleted", work=work)
    return {"deleted": True}


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


@router.get("/work/{workId}/wakes", response_model=WorkWakesResponse, summary="작업 wake 실행 대기열 조회")
async def list_work_wakes(
    request: Request,
    workId: str = Path(...),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> WorkWakesResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    items = request.app.state.work_repository.list_work_wakes(workId, limit=limit, offset=offset)
    return WorkWakesResponse(items=[_wake_response(item) for item in items], totalCount=len(items))


@router.get("/work/{workId}/recovery-actions", response_model=WorkRecoveryActionsResponse, summary="작업 실행 복구 기록 조회")
async def list_work_recovery_actions(
    request: Request,
    workId: str = Path(...),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> WorkRecoveryActionsResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    items = request.app.state.work_repository.list_recovery_actions(workId, limit=limit, offset=offset)
    return WorkRecoveryActionsResponse(items=[_recovery_action_response(item) for item in items], totalCount=len(items))


@router.post("/work/{workId}/runs", response_model=WorkCreateResponse, summary="작업 실행 시작")
async def create_work_run(request: Request, payload: CreateWorkRunRequest, workId: str = Path(...)) -> WorkCreateResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    if work.active_run_id:
        raise HTTPException(status_code=409, detail="work already has an active run")
    unresolved_blocker_ids = _unresolved_blocker_work_ids(request.app.state.work_repository, work.work_id)
    if unresolved_blocker_ids:
        wakes = await enqueue_work_graph_wake(request, user=user, work=work, reason="manual_run_blocked")
        updated = request.app.state.work_repository.get_work(work.work_id) or work
        await _publish_work_event(request, str(user.user_id), "work_run.queued", work=updated)
        if wakes:
            first_wake = wakes[0]
            return WorkCreateResponse(
                work=_work_response(updated, repository=request.app.state.work_repository),
                taskRunId=getattr(first_wake, "task_run_id", None),
                taskStatus="QUEUED",
            )
        raise HTTPException(
            status_code=409,
            detail={
                "message": "work is blocked by unresolved blockers",
                "unresolvedBlockerWorkIds": unresolved_blocker_ids,
            },
        )
    message = await _create_message_in_session(
        request,
        CreateSessionMessageRequest(
            content=payload.message.strip() or "이 작업을 이어서 진행해.",
            clientMessageId=payload.client_message_id,
            inputPayload={"workId": work.work_id},
        ),
        session=_session_or_404(request, work.session_id),
        user=user,
        run_in_background=True,
    )
    updated = request.app.state.work_repository.get_work(work.work_id) or work
    await _publish_work_event(request, str(user.user_id), "work_run.created", work=updated)
    return WorkCreateResponse(work=_work_response(updated, repository=request.app.state.work_repository), taskRunId=message.task_run_id, taskStatus=message.status)


@router.post("/work-runs/{runId}/cancel", response_model=WorkRunResponse, summary="작업 실행 취소")
async def cancel_work_run(request: Request, runId: str = Path(...)) -> WorkRunResponse:
    user = await authenticate_http_user(request)
    work = request.app.state.work_repository.get_work_by_task_run_id(runId)
    if work is None:
        raise HTTPException(status_code=404, detail="work run not found")
    _ensure_work_owner(user, work)
    task = await request.app.state.orchestrator.cancel(task_run_id=runId)
    link = request.app.state.work_repository.update_run_status(work.work_id, runId, str(task.status))
    updated = request.app.state.work_repository.get_work(work.work_id) or work
    await _publish_work_event(request, str(user.user_id), "work_run.cancelled", work=updated)
    return _run_response(link)


@router.get("/work/{workId}/relations", response_model=WorkRelationsResponse, summary="작업 관계 목록")
async def list_work_relations(request: Request, workId: str = Path(...)) -> WorkRelationsResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    items = request.app.state.work_repository.list_relations(workId)
    return WorkRelationsResponse(items=[_relation_response(item) for item in items], totalCount=len(items))


@router.post("/work/{workId}/relations", response_model=WorkRelationResponse, summary="작업 관계 추가")
async def add_work_relation(request: Request, payload: UpsertWorkRelationRequest, workId: str = Path(...)) -> WorkRelationResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    target = _work_or_404(request, payload.target_work_id)
    _ensure_work_owner(user, work)
    _ensure_work_owner(user, target)
    if work.session_id != target.session_id:
        raise HTTPException(status_code=409, detail="target work belongs to another session")
    relation_type = _normalize_relation_type(payload.relation_type)
    relation = request.app.state.work_repository.add_relation(source_work_id=workId, target_work_id=target.work_id, relation_type=relation_type)
    updated = request.app.state.work_repository.get_work(workId) or work
    await _publish_work_event(request, str(user.user_id), "work.updated", work=updated)
    return _relation_response(relation)


@router.delete("/work/{workId}/relations/{relationType}/{targetWorkId}", response_model=dict, summary="작업 관계 삭제")
async def remove_work_relation(request: Request, workId: str = Path(...), relationType: str = Path(...), targetWorkId: str = Path(...)) -> dict[str, bool]:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    target = _work_or_404(request, targetWorkId)
    _ensure_work_owner(user, work)
    _ensure_work_owner(user, target)
    normalized_relation_type = _normalize_relation_type(relationType)
    deleted = request.app.state.work_repository.remove_relation(source_work_id=workId, target_work_id=targetWorkId, relation_type=normalized_relation_type)
    if deleted and normalized_relation_type == "blocks":
        await enqueue_work_graph_wake(request, user=user, work=target, reason="blockers_resolved")
    await _publish_work_event(request, str(user.user_id), "work.updated", work=work)
    return {"deleted": deleted}


@router.get("/work/{workId}/documents", response_model=WorkDocumentsResponse, summary="작업 문서 목록")
async def list_work_documents(request: Request, workId: str = Path(...)) -> WorkDocumentsResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    items = request.app.state.work_repository.list_documents(workId)
    return WorkDocumentsResponse(items=[_document_response(item) for item in items], totalCount=len(items))


@router.put("/work/{workId}/documents/{documentKey}", response_model=WorkDocumentResponse, summary="작업 문서 저장")
async def upsert_work_document(
    request: Request,
    payload: UpsertWorkDocumentRequest,
    workId: str = Path(...),
    documentKey: str = Path(...),
) -> WorkDocumentResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    document = request.app.state.work_repository.upsert_document(
        work_id=workId,
        document_key=_safe_document_key(documentKey),
        title=payload.title.strip(),
        body=payload.body,
        format=payload.format.strip() or "markdown",
        actor_id=str(user.user_id),
    )
    await _publish_simple_event(
        request,
        str(user.user_id),
        "work_document.updated",
        {"document": _document_response(document).model_dump(mode="json", by_alias=True), "workId": workId},
    )
    return _document_response(document)


@router.delete("/work/{workId}/documents/{documentKey}", response_model=dict, summary="작업 문서 삭제")
async def delete_work_document(request: Request, workId: str = Path(...), documentKey: str = Path(...)) -> dict[str, bool]:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    deleted = request.app.state.work_repository.delete_document(workId, _safe_document_key(documentKey))
    await _publish_simple_event(request, str(user.user_id), "work_document.deleted", {"workId": workId, "documentKey": documentKey})
    return {"deleted": deleted}


@router.get("/work/{workId}/documents/{documentKey}/revisions", response_model=WorkDocumentRevisionsResponse, summary="작업 문서 이력")
async def list_work_document_revisions(request: Request, workId: str = Path(...), documentKey: str = Path(...)) -> WorkDocumentRevisionsResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    items = request.app.state.work_repository.list_document_revisions(workId, _safe_document_key(documentKey))
    return WorkDocumentRevisionsResponse(items=[_document_revision_response(item) for item in items], totalCount=len(items))


@router.get("/work/{workId}/work-products", response_model=WorkProductsResponse, summary="작업 결과물 목록")
async def list_work_products(request: Request, workId: str = Path(...)) -> WorkProductsResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    items = request.app.state.work_repository.list_products(workId)
    return WorkProductsResponse(items=[_product_response(item) for item in items], totalCount=len(items))


@router.post("/work/{workId}/work-products", response_model=WorkProductResponse, summary="작업 결과물 추가")
async def create_work_product(request: Request, payload: CreateWorkProductRequest, workId: str = Path(...)) -> WorkProductResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    product = request.app.state.work_repository.create_product(
        work_id=workId,
        title=payload.title.strip(),
        summary=payload.summary,
        product_type=payload.product_type.strip() or "note",
        status=payload.status.strip() or "draft",
        review_state=payload.review_state.strip() or "none",
        uri=payload.uri,
        metadata=payload.metadata,
    )
    await _publish_simple_event(request, str(user.user_id), "work_product.created", {"product": _product_response(product).model_dump(mode="json", by_alias=True)})
    return _product_response(product)


@router.post("/work-products/{productId}/update-fields", response_model=WorkProductResponse, summary="작업 결과물 수정")
async def update_work_product(request: Request, payload: UpdateWorkProductRequest, productId: str = Path(...)) -> WorkProductResponse:
    user = await authenticate_http_user(request)
    product = _work_product_or_404(request, productId)
    work = _work_or_404(request, product.work_id)
    _ensure_work_owner(user, work)
    updated = request.app.state.work_repository.update_product(
        productId,
        title=payload.title.strip() if payload.title is not None else None,
        summary=payload.summary,
        status=payload.status.strip() if payload.status is not None else None,
        review_state=payload.review_state.strip() if payload.review_state is not None else None,
        uri=payload.uri,
        metadata=payload.metadata,
    )
    await _publish_simple_event(request, str(user.user_id), "work_product.updated", {"product": _product_response(updated).model_dump(mode="json", by_alias=True)})
    return _product_response(updated)


@router.delete("/work-products/{productId}", response_model=dict, summary="작업 결과물 삭제")
async def delete_work_product(request: Request, productId: str = Path(...)) -> dict[str, bool]:
    user = await authenticate_http_user(request)
    product = _work_product_or_404(request, productId)
    work = _work_or_404(request, product.work_id)
    _ensure_work_owner(user, work)
    deleted = request.app.state.work_repository.delete_product(productId)
    await _publish_simple_event(request, str(user.user_id), "work_product.deleted", {"productId": productId, "workId": work.work_id})
    return {"deleted": deleted}


@router.get("/work/{workId}/interactions", response_model=WorkInteractionsResponse, summary="작업 상호작용 목록")
async def list_work_interactions(request: Request, workId: str = Path(...)) -> WorkInteractionsResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    items = request.app.state.work_repository.list_interactions(workId)
    return WorkInteractionsResponse(items=[_interaction_response(item) for item in items], totalCount=len(items))


@router.post("/work/{workId}/interactions", response_model=WorkInteractionResponse, summary="작업 상호작용 추가")
async def create_work_interaction(request: Request, payload: CreateWorkInteractionRequest, workId: str = Path(...)) -> WorkInteractionResponse:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    interaction = request.app.state.work_repository.create_interaction(
        work_id=workId,
        kind=_normalize_interaction_kind(payload.kind),
        title=payload.title.strip() if payload.title else None,
        body=payload.body,
        payload=payload.payload,
        continuation_policy=_normalize_continuation_policy(payload.continuation_policy),
    )
    await _publish_simple_event(request, str(user.user_id), "work_interaction.created", {"interaction": _interaction_response(interaction).model_dump(mode="json", by_alias=True)})
    return _interaction_response(interaction)


@router.post("/work-interactions/{interactionId}/accept", response_model=WorkInteractionResponse, summary="작업 상호작용 수락")
async def accept_work_interaction(request: Request, interactionId: str = Path(...)) -> WorkInteractionResponse:
    return await _update_interaction_status(request, interactionId=interactionId, status="accepted")


@router.post("/work-interactions/{interactionId}/reject", response_model=WorkInteractionResponse, summary="작업 상호작용 거절")
async def reject_work_interaction(request: Request, interactionId: str = Path(...)) -> WorkInteractionResponse:
    return await _update_interaction_status(request, interactionId=interactionId, status="rejected")


@router.post("/work-interactions/{interactionId}/cancel", response_model=WorkInteractionResponse, summary="작업 상호작용 취소")
async def cancel_work_interaction(request: Request, interactionId: str = Path(...)) -> WorkInteractionResponse:
    return await _update_interaction_status(request, interactionId=interactionId, status="cancelled")


@router.post("/work-interactions/{interactionId}/respond", response_model=WorkInteractionResponse, summary="작업 상호작용 응답")
async def respond_work_interaction(request: Request, payload: RespondWorkInteractionRequest, interactionId: str = Path(...)) -> WorkInteractionResponse:
    return await _update_interaction_status(request, interactionId=interactionId, status="answered", response=payload.response)


@router.post("/work/{workId}/read", response_model=dict, summary="작업 읽음 처리")
async def mark_work_read(request: Request, workId: str = Path(...)) -> dict[str, bool]:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    owner_user_id = _int_or_none(user.user_id)
    if owner_user_id is None:
        raise HTTPException(status_code=400, detail="owner user id is required")
    request.app.state.work_repository.mark_read(workId, owner_user_id=owner_user_id)
    return {"ok": True}


@router.delete("/work/{workId}/read", response_model=dict, summary="작업 읽지 않음 처리")
async def mark_work_unread(request: Request, workId: str = Path(...)) -> dict[str, bool]:
    user = await authenticate_http_user(request)
    work = _work_or_404(request, workId)
    _ensure_work_owner(user, work)
    owner_user_id = _int_or_none(user.user_id)
    if owner_user_id is None:
        raise HTTPException(status_code=400, detail="owner user id is required")
    request.app.state.work_repository.mark_unread(workId, owner_user_id=owner_user_id)
    return {"ok": True}


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


def _work_product_or_404(request: Request, product_id: str):
    product = request.app.state.work_repository.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="work product not found")
    return product


def _ensure_work_owner(user, work: WorkItem) -> None:
    ensure_owner(user, work.owner_key)


def _work_response(work: WorkItem, *, repository=None) -> WorkItemResponse:
    data = WorkItemResponse.model_validate(work, from_attributes=True).model_dump(by_alias=True)
    if repository is not None:
        labels = _safe_label_ids(repository, work.work_id)
        children = _safe_children(repository, work)
        relations = _safe_relations(repository, work.work_id)
        runs = _safe_runs(repository, work.work_id)
        comments = _safe_comments(repository, work.work_id)
        data.update(
            {
                "labelIds": labels,
                "childCount": len(children),
                "completedChildCount": len([child for child in children if child.status in {"done", "cancelled"}]),
                "blockedByCount": len([relation for relation in relations if relation.relation_type == "blocks" and relation.source_work_id != work.work_id]),
                "recentRunIds": [run.task_run_id for run in runs[:5]],
                "commentCount": len(comments),
                "blockedByWorkIds": [
                    relation.source_work_id
                    for relation in relations
                    if relation.relation_type == "blocks" and relation.target_work_id == work.work_id
                ],
                "relatedWorkIds": [
                    relation.target_work_id if relation.source_work_id == work.work_id else relation.source_work_id
                    for relation in relations
                    if relation.relation_type == "related"
                ],
                "childWorkIds": [child.work_id for child in children],
            }
        )
    return WorkItemResponse.model_validate(data)


def _comment_response(comment) -> WorkCommentResponse:
    return WorkCommentResponse.model_validate(comment, from_attributes=True)


def _label_response(label) -> WorkLabelResponse:
    return WorkLabelResponse.model_validate(label, from_attributes=True)


def _relation_response(relation) -> WorkRelationResponse:
    return WorkRelationResponse.model_validate(relation, from_attributes=True)


def _run_response(run) -> WorkRunResponse:
    return WorkRunResponse.model_validate(run, from_attributes=True)


def _wake_response(wake) -> WorkWakeResponse:
    return WorkWakeResponse.model_validate(wake, from_attributes=True)


def _recovery_action_response(action) -> WorkRecoveryActionResponse:
    return WorkRecoveryActionResponse.model_validate(action, from_attributes=True)


def _document_response(document) -> WorkDocumentResponse:
    return WorkDocumentResponse.model_validate(document, from_attributes=True)


def _document_revision_response(revision) -> WorkDocumentRevisionResponse:
    return WorkDocumentRevisionResponse.model_validate(revision, from_attributes=True)


def _product_response(product) -> WorkProductResponse:
    return WorkProductResponse.model_validate(product, from_attributes=True)


def _interaction_response(interaction) -> WorkInteractionResponse:
    return WorkInteractionResponse.model_validate(interaction, from_attributes=True)


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
        "work": _work_response(work, repository=getattr(request.app.state, "work_repository", None)).model_dump(mode="json", by_alias=True),
    }
    if comment is not None:
        payload["comment"] = _comment_response(comment).model_dump(mode="json", by_alias=True)
    await manager.broadcast(
        {"protocolVersion": 1, "type": event_type, "payload": payload},
        f"work:{owner_key}",
    )


async def _publish_label_event(request: Request, owner_key: str, event_type: str, *, label) -> None:
    await _publish_simple_event(
        request,
        owner_key,
        event_type,
        {"label": _label_response(label).model_dump(mode="json", by_alias=True)},
    )


async def _publish_simple_event(request: Request, owner_key: str, event_type: str, payload: dict[str, Any]) -> None:
    manager = getattr(request.app.state, "ws_manager", None)
    if manager is None:
        return
    await manager.broadcast({"protocolVersion": 1, "type": event_type, "payload": payload}, f"work:{owner_key}")


def _safe_label_ids(repository, work_id: str) -> list[str]:
    try:
        rows = repository.connection_factory().execute("SELECT label_id FROM work_label_links WHERE work_id = %s", (work_id,)).fetchall()
        return [str(dict(row)["label_id"]) for row in rows]
    except Exception:
        return []


def _safe_children(repository, work: WorkItem) -> list[WorkItem]:
    try:
        return repository.list_children(work.work_id)
    except Exception:
        return []


def _list_descendant_works(repository, work_id: str) -> list[WorkItem]:
    descendants: list[WorkItem] = []
    queue = list(repository.list_children(work_id))
    while queue:
        child = queue.pop(0)
        descendants.append(child)
        queue.extend(repository.list_children(child.work_id))
    return descendants


def _safe_relations(repository, work_id: str):
    try:
        return repository.list_relations(work_id)
    except Exception:
        return []


def _safe_runs(repository, work_id: str):
    try:
        return repository.list_runs(work_id, limit=5)
    except Exception:
        return []


def _safe_comments(repository, work_id: str):
    try:
        return repository.list_comments(work_id, limit=500)
    except Exception:
        return []


def _unresolved_blocker_work_ids(repository, work_id: str) -> list[str]:
    try:
        relations = repository.list_relations(work_id)
    except Exception:
        return []
    blocker_ids = [
        relation.source_work_id
        for relation in relations
        if relation.relation_type == "blocks" and relation.target_work_id == work_id
    ]
    unresolved: list[str] = []
    for blocker_id in dict.fromkeys(blocker_ids):
        blocker = repository.get_work(blocker_id)
        if blocker is None or blocker.status != "done":
            unresolved.append(blocker_id)
    return unresolved


def _validate_assignee_or_400(request: Request, *, session_id: str, owner_key: str, assignee_agent_id: Any) -> None:
    assignee = str(assignee_agent_id or "").strip()
    if not assignee or assignee == "CEO":
        return
    profile = request.app.state.agent_repository.get_session_agent(profile_id=assignee, owner_key=owner_key)
    if profile is None or profile.get("session_id") != session_id or profile.get("agent_type") != "user_subagent":
        raise HTTPException(status_code=400, detail="invalid work assignee")


def _normalize_relation_type(value: str) -> str:
    relation_type = str(value or "").strip().lower()
    if relation_type not in {"blocks", "related"}:
        raise HTTPException(status_code=400, detail="invalid work relation type")
    return relation_type


def _normalize_interaction_kind(value: str) -> str:
    kind = str(value or "").strip()
    if kind not in {"suggest_tasks", "ask_user_questions", "request_confirmation"}:
        raise HTTPException(status_code=400, detail="invalid work interaction kind")
    return kind


def _normalize_continuation_policy(value: str) -> str:
    policy = str(value or "none").strip()
    if policy not in {"none", "wake_assignee", "wake_assignee_on_accept"}:
        raise HTTPException(status_code=400, detail="invalid continuation policy")
    return policy


def _safe_document_key(value: str) -> str:
    key = str(value or "").strip()
    if not key or ".." in key or key.startswith("/") or "\\" in key:
        raise HTTPException(status_code=400, detail="invalid document key")
    return key[:160]


def _would_create_parent_cycle(repository, *, work_id: str, parent_id: str) -> bool:
    cursor = repository.get_work(parent_id)
    seen: set[str] = set()
    while cursor is not None and cursor.parent_id:
        if cursor.work_id in seen:
            return True
        seen.add(cursor.work_id)
        if cursor.parent_id == work_id:
            return True
        cursor = repository.get_work(cursor.parent_id)
    return False


async def _update_interaction_status(
    request: Request,
    *,
    interactionId: str | None = None,
    interaction_id: str | None = None,
    status: str,
    response: dict[str, Any] | None = None,
) -> WorkInteractionResponse:
    user = await authenticate_http_user(request)
    target_id = interaction_id or interactionId
    if target_id is None:
        raise HTTPException(status_code=404, detail="work interaction not found")
    existing = _find_interaction_or_404(request, target_id)
    work = _work_or_404(request, existing.work_id)
    _ensure_work_owner(user, work)
    updated = request.app.state.work_repository.update_interaction(target_id, status=status, response=response)
    await _publish_simple_event(
        request,
        str(user.user_id),
        "work_interaction.updated",
        {"interaction": _interaction_response(updated).model_dump(mode="json", by_alias=True)},
    )
    if updated.continuation_policy == "wake_assignee" or (updated.continuation_policy == "wake_assignee_on_accept" and status == "accepted"):
        await _wake_work_from_interaction(request, user=user, work=work, interaction=updated)
    return _interaction_response(updated)


def _find_interaction_or_404(request: Request, interaction_id: str):
    interaction = request.app.state.work_repository.get_interaction(interaction_id)
    if interaction is None:
        raise HTTPException(status_code=404, detail="work interaction not found")
    return interaction


def _label_color(value: str | None) -> str:
    text = str(value or "#64748b").strip()
    if not re.match(r"^#[0-9a-fA-F]{6}$", text):
        return "#64748b"
    return text


async def _wake_work_from_comment(request: Request, *, user, work: WorkItem, comment) -> None:
    if work.active_run_id:
        _enqueue_comment_followup_wake(request, work=work, comment=comment)
        return
    if work.status == "backlog" or work.status == "cancelled":
        return
    if _unresolved_blocker_work_ids(request.app.state.work_repository, work.work_id):
        return
    if work.status == "done" and not bool(getattr(comment, "resume_requested", False)):
        return
    message = str(getattr(comment, "body", "") or "").strip() or "댓글을 반영해서 이 작업을 이어서 진행해."
    try:
        await _create_message_in_session(
            request,
            CreateSessionMessageRequest(
                content=message,
                clientMessageId=f"work-comment:{getattr(comment, 'comment_id', '')}",
                inputPayload={"workId": work.work_id},
            ),
            session=_session_or_404(request, work.session_id),
            user=user,
        )
    except Exception as error:
        request.app.state.work_repository.add_comment(
            WorkComment(
                comment_id=new_id("comment"),
                work_id=work.work_id,
                author_type="system",
                body=f"댓글 실행 시작 실패: {error}",
            )
        )


def _enqueue_comment_followup_wake(request: Request, *, work: WorkItem, comment) -> None:
    enqueue_wake = getattr(request.app.state.work_repository, "enqueue_work_wake", None)
    if not callable(enqueue_wake):
        return
    reason = "issue_reopened_via_comment" if bool(getattr(comment, "resume_requested", False)) else "issue_commented"
    enqueue_wake(
        WorkWakeRequest(
            wake_id=new_id("work_wake"),
            work_id=work.work_id,
            root_work_id=work.work_id,
            reason=reason,
            status="scheduled_retry",
            requested_by_task_run_id=work.active_run_id,
            last_error="work already has an active run",
        )
    )


def _effective_comment_resume_requested(
    *,
    work: WorkItem,
    payload_resume: bool,
    unresolved_blocker_ids: list[str],
) -> bool:
    if not payload_resume:
        return False
    if work.status == "blocked" and unresolved_blocker_ids:
        return False
    return True


def _should_reopen_blocked_work_from_comment(*, work: WorkItem, unresolved_blocker_ids: list[str]) -> bool:
    return work.status == "blocked" and not unresolved_blocker_ids


async def _wake_work_from_interaction(request: Request, *, user, work: WorkItem, interaction) -> None:
    if work.active_run_id or work.status in {"backlog", "cancelled"}:
        return
    if _unresolved_blocker_work_ids(request.app.state.work_repository, work.work_id):
        return
    title = getattr(interaction, "title", None) or "사용자 응답 반영"
    try:
        await _create_message_in_session(
            request,
            CreateSessionMessageRequest(
                content=f"{title} 내용을 반영해서 이 작업을 이어서 진행해.",
                clientMessageId=f"work-interaction:{getattr(interaction, 'interaction_id', '')}",
                inputPayload={"workId": work.work_id},
            ),
            session=_session_or_404(request, work.session_id),
            user=user,
        )
    except Exception as error:
        request.app.state.work_repository.add_comment(
            WorkComment(
                comment_id=new_id("comment"),
                work_id=work.work_id,
                author_type="system",
                body=f"응답 반영 실행 시작 실패: {error}",
            )
        )
