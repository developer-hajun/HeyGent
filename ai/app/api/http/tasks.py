from __future__ import annotations

from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.deps.http_auth import authenticate_http_user, ensure_owner
from app.api.deps.task_context import TaskContext, get_task_context
from app.core.time import utc_now
from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_request import CreateTaskRequest, ResumeTaskRequest
from app.contracts.task.task_response import (
    ActiveTaskRunCurrentStepResponse,
    ActiveTaskRunListItemResponse,
    ActiveTaskRunListResponse,
    PendingApprovalResponse,
    StepRunResponse,
    StepRunSummaryResponse,
    TaskEventResponse,
    TaskRunFlowActivityResponse,
    TaskRunFlowEdgeResponse,
    TaskRunFlowNodeResponse,
    TaskRunFlowResponse,
    TaskRunFlowSemanticResponse,
    TaskRunFlowWorkerSessionResponse,
    TaskRunListItemResponse,
    TaskRunListResponse,
    TaskRunResponse,
)
from app.contracts.task.task_status import TaskStatus
from app.domain.orchestration.contracts import OrchestrationRequest
from app.domain.tasks.models import StepRun

router = APIRouter(prefix="/taskRuns", tags=["taskRuns"])

_ACTIVE_TASK_STATUSES = [status.value for status in (TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.WAITING, TaskStatus.BLOCKED)]
_RECENT_TERMINAL_TASK_STATUSES = [status.value for status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED)]
_ACTIVE_STEP_STATUSES = {status.value for status in (StepStatus.PENDING, StepStatus.RUNNING, StepStatus.WAITING, StepStatus.BLOCKED)}
_RECENT_ACTIVE_TTL_SECONDS = 300
_TASK_TITLE_FALLBACKS = {
    "agent.loop": "agent loop 실행",
}


def _select_product_session_id(request: Request, legacy_session_key: str | None) -> str | None:
    product_session_id = request.query_params.get("productSessionId")
    if product_session_id is not None:
        normalized = product_session_id.strip()
        if normalized:
            return normalized
    return legacy_session_key


def _normalize_task_status_filter(raw_status: str) -> str | None:
    normalized = (raw_status or "ALL").strip().upper()
    if normalized == "ALL":
        return None
    if normalized not in {status.value for status in TaskStatus}:
        raise HTTPException(status_code=400, detail=f"invalid status filter: {raw_status}")
    return normalized


def _select_current_step(task, steps: list[StepRun]) -> StepRun | None:
    """상세/목록 양쪽에서 보여 줄 대표 StepRun 을 고른다.

    아직 여러 step 이 쌓이지 않는 MVP 구조라도,
    앞으로 멀티 스텝으로 확장될 것을 감안해 활성 step 우선 규칙을 고정해 둔다.
    """

    if task.current_step_run_id:
        for step in steps:
            if step.step_run_id == task.current_step_run_id:
                return step
    for step in steps:
        if step.status in _ACTIVE_STEP_STATUSES:
            return step
    return steps[-1] if steps else None


def _truncate_text(value: str, *, limit: int = 56) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"



def _find_first_scalar(payload: dict) -> str | None:
    for value in payload.values():
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, (int, float, bool)):
            return str(value)
    return None



def _summarize_task_input_payload(payload: dict) -> str | None:
    """Task 목록에서 사용자 의도를 빠르게 파악할 수 있도록 입력을 한 줄로 요약한다."""

    preferred_keys = ["prompt", "message", "subject", "title", "query", "content", "text"]
    for key in preferred_keys:
        raw_value = payload.get(key)
        if isinstance(raw_value, str) and raw_value.strip():
            return _truncate_text(raw_value)
    first_scalar = _find_first_scalar(payload)
    if first_scalar:
        return _truncate_text(first_scalar)
    if payload:
        return _truncate_text(str(payload))
    return None



def _display_task_title(task, *, input_summary: str | None) -> str:
    raw_title = (task.title or "").strip()
    if raw_title and raw_title not in {task.task_type, task.intent_type}:
        return raw_title
    if task.task_type in _TASK_TITLE_FALLBACKS:
        return _TASK_TITLE_FALLBACKS[task.task_type]
    if input_summary:
        return _truncate_text(input_summary, limit=28)
    return task.intent_type or task.task_type



def _build_task_list_item(task, steps: list[StepRun]) -> TaskRunListItemResponse:
    current_step = _select_current_step(task, steps)
    current_step_response = None
    if current_step is not None:
        current_step_response = StepRunSummaryResponse.model_validate(current_step, from_attributes=True)
    input_summary = _summarize_task_input_payload(task.input_payload)
    return TaskRunListItemResponse(
        task_run_id=task.task_run_id,
        task_type=task.task_type,
        intent_type=task.intent_type,
        entry_executor_key=task.entry_executor_key,
        session_key=task.session_key,
        status=task.status,
        title=_display_task_title(task, input_summary=input_summary),
        input_summary=input_summary,
        step_count=len(steps),
        progress_summary=task.progress_summary,
        created_at=task.created_at,
        updated_at=task.updated_at,
        current_step=current_step_response,
    )


def _build_active_task_item(
    task,
    steps: list[StepRun],
    *,
    source: str,
    pending_approval: PendingApprovalResponse | None = None,
) -> ActiveTaskRunListItemResponse:
    current_step = _select_current_step(task, steps)
    current_step_response = None
    if current_step is not None:
        current_step_response = ActiveTaskRunCurrentStepResponse(
            step_run_id=current_step.step_run_id,
            title=current_step.title,
            status=current_step.status,
            executor_key=current_step.executor_key,
        )
    input_summary = _summarize_task_input_payload(task.input_payload)
    return ActiveTaskRunListItemResponse(
        task_run_id=task.task_run_id,
        source=source,
        session_key=task.session_key,
        status=task.status,
        title=_display_task_title(task, input_summary=input_summary),
        current_step_run_id=task.current_step_run_id,
        current_step=current_step_response,
        updated_at=task.updated_at,
        wait_reason=(task.wait_payload or {}).get("reason"),
        pending_approval=pending_approval,
    )


def _projection_steps(context: TaskContext, task_run_id: str) -> list[StepRun]:
    """Redis projection에 남은 StepRun snapshot을 순서대로 복원한다."""

    projection = context.task_projection_store
    if projection is None:
        return []
    steps: list[StepRun] = []
    for step_run_id in projection.list_task_steps(task_run_id):
        step = projection.get_step_snapshot(step_run_id)
        if step is not None:
            steps.append(step)
    return steps


def _build_active_items_from_projection(
    *,
    session_key: str,
    context: TaskContext,
) -> dict[str, ActiveTaskRunListItemResponse]:
    """Redis projection이 살아 있으면 active 목록을 DB 조회 전에 빠르게 만든다."""

    projection = context.task_projection_store
    if projection is None:
        return {}

    items_by_task_run_id: dict[str, ActiveTaskRunListItemResponse] = {}
    for task_run_id in projection.list_active_task_ids(session_key=session_key):
        task = projection.get_task_snapshot(task_run_id)
        if task is None:
            continue
        steps = _projection_steps(context, task.task_run_id)
        pending_approval = _build_pending_approval_response(context.repository.get_open_approval(task.task_run_id))
        items_by_task_run_id[task.task_run_id] = _build_active_task_item(
            task,
            steps,
            source="active",
            pending_approval=pending_approval,
        )
    return items_by_task_run_id


def _build_pending_approval_response(approval: dict | None) -> PendingApprovalResponse | None:
    """저장소의 approval row를 UI/API가 쓰는 pending approval 응답으로 정규화한다."""

    if approval is None or approval.get("status") != "PENDING":
        return None
    request_payload = approval.get("request_payload") or {}
    reason = request_payload.get("reason") or request_payload.get("approvalReason")
    tool_call_id = (
        request_payload.get("pending_tool_call_id")
        or request_payload.get("tool_call_id")
        or request_payload.get("toolCallId")
    )
    tool_name = (
        request_payload.get("pending_tool_name")
        or request_payload.get("tool_name")
        or request_payload.get("toolName")
    )
    return PendingApprovalResponse(
        approval_id=approval["approval_id"],
        step_run_id=approval.get("step_run_id"),
        status=approval["status"],
        reason=reason,
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        requested_at=approval.get("created_at"),
        can_approve=True,
        can_reject=True,
    )


def _build_task_response(task, context: TaskContext) -> TaskRunResponse:
    """TaskRun 응답에는 현재 열려 있는 approval 정보를 함께 붙인다."""

    response = TaskRunResponse.model_validate(task, from_attributes=True)
    response.pending_approval = _build_pending_approval_response(context.repository.get_open_approval(task.task_run_id))
    return response


def _has_active_task_for_owner_session(context: TaskContext, *, owner_key: str, session_key: str) -> bool:
    """productSessionId 중복 실행 제한은 인증 owner 범위 안에서만 적용한다."""

    active_total = context.repository.count_tasks_by_statuses(_ACTIVE_TASK_STATUSES, session_key=session_key)
    active_tasks = context.repository.list_tasks_by_statuses(
        _ACTIVE_TASK_STATUSES,
        session_key=session_key,
        limit=max(active_total, 1),
        offset=0,
    )
    return any(str(task.owner_key) == str(owner_key) for task in active_tasks)


def _recent_task_reference_time(task):
    return task.ended_at or task.updated_at or task.created_at


def _is_recent_terminal_task(task, *, now, ttl_seconds: int) -> bool:
    if task.status not in _RECENT_TERMINAL_TASK_STATUSES:
        return False
    reference_time = _recent_task_reference_time(task)
    if reference_time is None:
        return False
    return reference_time >= now - timedelta(seconds=ttl_seconds)


def _sort_active_snapshot_items(items: list[ActiveTaskRunListItemResponse]) -> list[ActiveTaskRunListItemResponse]:
    source_priority = {"active": 0, "recent": 1}
    return sorted(
        items,
        key=lambda item: (
            source_priority.get(item.source, 99),
            -(item.updated_at.timestamp() if item.updated_at is not None else 0),
        ),
    )


def _build_flow_activity_map(events: list) -> dict[str, list[TaskRunFlowActivityResponse]]:
    activity_by_step: dict[str, list[TaskRunFlowActivityResponse]] = {}
    for event in events:
        step_run_id = str(event.step_run_id or "").strip()
        if not step_run_id:
            continue
        activity_by_step.setdefault(step_run_id, []).append(
            TaskRunFlowActivityResponse(
                event_type=event.event_type,
                status=event.status,
                summary_message=event.summary_message,
                occurred_at=event.occurred_at,
            )
        )
    return activity_by_step


def _build_flow_nodes(task, steps: list[StepRun], *, activity_by_step: dict[str, list[TaskRunFlowActivityResponse]]) -> list[TaskRunFlowNodeResponse]:
    nodes: list[TaskRunFlowNodeResponse] = []
    for step in steps:
        semantic_detail = (step.detail_json or {}).get("semanticDetail") or {}
        agent_detail = (step.detail_json or {}).get("agentDetail") or {}
        semantic = None
        if semantic_detail:
            semantic = TaskRunFlowSemanticResponse(
                key=semantic_detail.get("semanticKey"),
                step=semantic_detail.get("semanticStep") or step.title,
                goal=semantic_detail.get("goal"),
                status=semantic_detail.get("status"),
            )
        worker_session = None
        worker_session_id = str(agent_detail.get("workerSessionId") or "").strip() or None
        if worker_session_id is not None:
            worker_session = TaskRunFlowWorkerSessionResponse(
                session_id=worker_session_id,
                status=agent_detail.get("status"),
                summary=agent_detail.get("summary"),
                agent_id=agent_detail.get("agentId"),
                profile_key=agent_detail.get("profileKey"),
            )
        nodes.append(
            TaskRunFlowNodeResponse(
                step_run_id=step.step_run_id,
                step_order=step.step_order,
                title=step.title,
                status=step.status,
                step_type=step.step_type,
                executor_key=step.executor_key,
                semantic=semantic,
                is_current=step.step_run_id == task.current_step_run_id,
                is_projected=bool((step.input_payload or {}).get("todo_key")),
                worker_session_id=worker_session_id,
                worker_session=worker_session,
                activity=activity_by_step.get(step.step_run_id, []),
            )
        )
    return nodes


def _build_step_response(
    task,
    step: StepRun,
    *,
    pending_approval: PendingApprovalResponse | None = None,
) -> StepRunResponse:
    semantic_detail = (step.detail_json or {}).get("semanticDetail") or {}
    agent_detail = (step.detail_json or {}).get("agentDetail") or {}
    semantic = None
    if semantic_detail:
        semantic = TaskRunFlowSemanticResponse(
            key=semantic_detail.get("semanticKey"),
            step=semantic_detail.get("semanticStep") or step.title,
            goal=semantic_detail.get("goal"),
            status=semantic_detail.get("status"),
        )
    worker_session = None
    worker_session_id = str(agent_detail.get("workerSessionId") or "").strip() or None
    if worker_session_id is not None:
        worker_session = TaskRunFlowWorkerSessionResponse(
            session_id=worker_session_id,
            status=agent_detail.get("status"),
            summary=agent_detail.get("summary"),
            agent_id=agent_detail.get("agentId"),
            profile_key=agent_detail.get("profileKey"),
        )
    return StepRunResponse(
        step_run_id=step.step_run_id,
        task_run_id=step.task_run_id,
        step_order=step.step_order,
        step_type=step.step_type,
        status=step.status,
        executor_key=step.executor_key,
        title=step.title,
        semantic=semantic,
        is_current=step.step_run_id == task.current_step_run_id,
        is_projected=bool((step.input_payload or {}).get("todo_key")),
        worker_session_id=worker_session_id,
        worker_session=worker_session,
        input_payload=step.input_payload,
        output_payload=step.output_payload,
        wait_payload=step.wait_payload,
        pending_approval=pending_approval,
        detail_json=step.detail_json,
        summary_message=step.summary_message,
        error_message=step.error_message,
        created_at=step.created_at,
        updated_at=step.updated_at,
        started_at=step.started_at,
        ended_at=step.ended_at,
    )


def _build_flow_edges(steps: list[StepRun]) -> list[TaskRunFlowEdgeResponse]:
    edges: list[TaskRunFlowEdgeResponse] = []
    for previous_step, next_step in zip(steps, steps[1:]):
        edges.append(
            TaskRunFlowEdgeResponse(
                from_step_run_id=previous_step.step_run_id,
                to_step_run_id=next_step.step_run_id,
                relation="next",
            )
        )
    for step in steps:
        worker_session_id = str((((step.detail_json or {}).get("agentDetail") or {}).get("workerSessionId")) or "").strip()
        if not worker_session_id:
            continue
        edges.append(
            TaskRunFlowEdgeResponse(
                from_step_run_id=step.step_run_id,
                to_agent_session_id=worker_session_id,
                relation="delegates_to",
            )
        )
    return edges


def _events_from_projection(
    context: TaskContext,
    task_run_id: str,
    *,
    after_sequence: int | None,
    limit: int,
) -> list[dict[str, Any]]:
    """재연결 복구용 recent event projection을 sequence window로 잘라낸다."""

    projection = context.task_projection_store
    if projection is None:
        return []

    events = projection.list_recent_events(task_run_id)
    if after_sequence is not None:
        events = [event for event in events if int(event.get("sequence") or 0) > after_sequence]
    return events[:limit]


@router.get("", response_model=TaskRunListResponse)
async def list_tasks(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=8, ge=1, le=20),
    status: str = Query(default="ALL"),
    session_key: str | None = Query(default=None, alias="sessionKey"),
    context: TaskContext = Depends(get_task_context),
) -> TaskRunListResponse:
    user = await authenticate_http_user(request)
    status_filter = _normalize_task_status_filter(status)
    offset = (page - 1) * page_size
    tasks = context.repository.list_tasks(status=status_filter, session_key=session_key, limit=page_size, offset=offset)
    if user is not None:
        tasks = [task for task in tasks if str(task.owner_key) == str(user.user_id)]
    total_count = context.repository.count_tasks(status=status_filter, session_key=session_key)
    if user is not None:
        # repository 계약이 owner filter를 아직 직접 받지 않으므로 인증 사용자의 현재 page 범위만 노출한다.
        total_count = len(tasks)
    items = [_build_task_list_item(task, context.repository.list_steps(task.task_run_id)) for task in tasks]
    return TaskRunListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total_count=total_count,
        has_previous=page > 1,
        has_next=offset + len(items) < total_count,
        status_filter=status_filter or "ALL",
    )


@router.get("/active", response_model=ActiveTaskRunListResponse)
async def list_active_tasks(
    request: Request,
    session_key: str | None = Query(default=None, alias="sessionKey"),
    context: TaskContext = Depends(get_task_context),
) -> ActiveTaskRunListResponse:
    user = await authenticate_http_user(request)
    session_key = _select_product_session_id(request, session_key)
    now = utc_now()
    items_by_task_run_id = (
        _build_active_items_from_projection(session_key=session_key, context=context)
        if session_key
        else {}
    )

    active_total_count = context.repository.count_tasks_by_statuses(_ACTIVE_TASK_STATUSES, session_key=session_key)
    active_tasks = context.repository.list_tasks_by_statuses(_ACTIVE_TASK_STATUSES, session_key=session_key, limit=max(active_total_count, 1), offset=0)

    recent_total_pool = context.repository.count_tasks_by_statuses(_RECENT_TERMINAL_TASK_STATUSES, session_key=session_key)
    recent_candidates = context.repository.list_tasks_by_statuses(
        _RECENT_TERMINAL_TASK_STATUSES,
        session_key=session_key,
        limit=max(recent_total_pool, 1),
        offset=0,
    )

    for task in active_tasks:
        if task.task_run_id in items_by_task_run_id:
            continue
        steps = context.repository.list_steps(task.task_run_id)
        pending_approval = _build_pending_approval_response(context.repository.get_open_approval(task.task_run_id))
        items_by_task_run_id[task.task_run_id] = _build_active_task_item(
            task,
            steps,
            source="active",
            pending_approval=pending_approval,
        )

    for task in recent_candidates:
        if not _is_recent_terminal_task(task, now=now, ttl_seconds=_RECENT_ACTIVE_TTL_SECONDS):
            continue
        if task.task_run_id in items_by_task_run_id:
            continue
        steps = context.repository.list_steps(task.task_run_id)
        items_by_task_run_id[task.task_run_id] = _build_active_task_item(task, steps, source="recent")

    items = _sort_active_snapshot_items(list(items_by_task_run_id.values()))
    if user is not None:
        filtered_items = []
        for item in items:
            task = context.repository.get_task(item.task_run_id)
            if task is not None and str(task.owner_key) == str(user.user_id):
                filtered_items.append(item)
        items = filtered_items
    return ActiveTaskRunListResponse(
        items=items,
        total_count=len(items),
    )


@router.post("", response_model=TaskRunResponse)
async def create_task(request: Request, payload: CreateTaskRequest, context: TaskContext = Depends(get_task_context)) -> TaskRunResponse:
    user = await authenticate_http_user(request)
    owner_key = user.user_id if user is not None else payload.owner_key
    orchestrator = request.app.state.orchestrator
    active_lock_task_id = None
    if payload.session_key:
        if _has_active_task_for_owner_session(context, owner_key=owner_key, session_key=payload.session_key):
            # 같은 사용자의 동일 product session만 막아 다른 사용자의 같은 외부 session id와 충돌하지 않게 한다.
            raise HTTPException(status_code=409, detail="active task already exists in this session")
        projection = context.task_projection_store
        if projection is not None:
            active_lock_task_id = f"pending:{owner_key}:{payload.session_key}"
            if not projection.acquire_active_session_lock(payload.session_key, active_lock_task_id, owner_key=owner_key):
                raise HTTPException(status_code=409, detail="active task already exists in this session")
    try:
        task = await orchestrator.start(
            OrchestrationRequest(
                owner_key=owner_key,
                session_key=payload.session_key,
                input_payload=payload.input_payload,
                intent_type=payload.intent_type,
                entry_executor_key=payload.entry_executor_key,
            )
        )
        if payload.session_key and active_lock_task_id and context.task_projection_store is not None:
            context.task_projection_store.release_active_session_lock(payload.session_key, active_lock_task_id, owner_key=owner_key)
            context.task_projection_store.acquire_active_session_lock(payload.session_key, task.task_run_id, owner_key=owner_key)
    except KeyError as error:
        if payload.session_key and active_lock_task_id and context.task_projection_store is not None:
            context.task_projection_store.release_active_session_lock(payload.session_key, active_lock_task_id, owner_key=owner_key)
        raise HTTPException(status_code=404, detail=f"unknown intent or executor: {error.args[0]}") from error
    except ValueError as error:
        if payload.session_key and active_lock_task_id and context.task_projection_store is not None:
            context.task_projection_store.release_active_session_lock(payload.session_key, active_lock_task_id, owner_key=owner_key)
        raise HTTPException(status_code=400, detail=str(error)) from error
    return _build_task_response(task, context)


@router.get("/{task_run_id}/flow", response_model=TaskRunFlowResponse)
async def get_task_flow(request: Request, task_run_id: str, context: TaskContext = Depends(get_task_context)) -> TaskRunFlowResponse:
    user = await authenticate_http_user(request)
    task = context.repository.get_task(task_run_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    ensure_owner(user, task.owner_key)
    steps = context.repository.list_steps(task_run_id)
    events = context.repository.list_events(task_run_id)
    input_summary = _summarize_task_input_payload(task.input_payload)
    activity_by_step = _build_flow_activity_map(events)
    return TaskRunFlowResponse(
        task_run_id=task.task_run_id,
        status=task.status,
        title=_display_task_title(task, input_summary=input_summary),
        current_step_run_id=task.current_step_run_id,
        entry_executor_key=task.entry_executor_key,
        summary=task.progress_summary,
        pending_approval=_build_pending_approval_response(context.repository.get_open_approval(task.task_run_id)),
        nodes=_build_flow_nodes(task, steps, activity_by_step=activity_by_step),
        edges=_build_flow_edges(steps),
    )


@router.get("/{task_run_id}", response_model=TaskRunResponse)
async def get_task(request: Request, task_run_id: str, context: TaskContext = Depends(get_task_context)) -> TaskRunResponse:
    user = await authenticate_http_user(request)
    task = context.repository.get_task(task_run_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    ensure_owner(user, task.owner_key)
    return _build_task_response(task, context)


@router.get("/{task_run_id}/steps", response_model=list[StepRunResponse])
async def list_steps(request: Request, task_run_id: str, context: TaskContext = Depends(get_task_context)) -> list[StepRunResponse]:
    user = await authenticate_http_user(request)
    task = context.repository.get_task(task_run_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    ensure_owner(user, task.owner_key)
    steps = context.repository.list_steps(task_run_id)
    pending_approval = _build_pending_approval_response(context.repository.get_open_approval(task_run_id))
    return [
        _build_step_response(
            task,
            step,
            pending_approval=pending_approval if pending_approval and pending_approval.step_run_id == step.step_run_id else None,
        )
        for step in steps
    ]


@router.get("/{task_run_id}/events", response_model=list[TaskEventResponse])
async def list_events(
    request: Request,
    task_run_id: str,
    after_sequence: int | None = Query(default=None, ge=0, alias="afterSequence"),
    limit: int = Query(default=200, ge=1, le=500),
    context: TaskContext = Depends(get_task_context),
) -> list[TaskEventResponse]:
    user = await authenticate_http_user(request)
    task = context.repository.get_task(task_run_id)
    if task is None and user is not None:
        raise HTTPException(status_code=404, detail="task not found")
    if task is not None:
        ensure_owner(user, task.owner_key)
    projected_events = _events_from_projection(
        context,
        task_run_id,
        after_sequence=after_sequence,
        limit=limit,
    )
    if projected_events:
        return [TaskEventResponse.model_validate(event, from_attributes=True) for event in projected_events]

    events = context.repository.list_events(task_run_id)
    return [TaskEventResponse.model_validate(event, from_attributes=True) for event in events[:limit]]


@router.post("/{task_run_id}/resume", response_model=TaskRunResponse)
async def resume_task(request: Request, task_run_id: str, payload: ResumeTaskRequest, context: TaskContext = Depends(get_task_context)) -> TaskRunResponse:
    user = await authenticate_http_user(request)
    current_task = context.repository.get_task(task_run_id)
    if current_task is None:
        raise HTTPException(status_code=404, detail="task not found")
    ensure_owner(user, current_task.owner_key)
    try:
        task = await request.app.state.orchestrator.resume(
            task_run_id=task_run_id,
            approval_id=payload.approval_id or "",
            payload=payload.payload,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="task not found") from None
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return _build_task_response(task, context)


@router.post("/{task_run_id}/cancel", response_model=TaskRunResponse)
async def cancel_task(request: Request, task_run_id: str, context: TaskContext = Depends(get_task_context)) -> TaskRunResponse:
    user = await authenticate_http_user(request)
    current_task = context.repository.get_task(task_run_id)
    if current_task is None:
        raise HTTPException(status_code=404, detail="task not found")
    ensure_owner(user, current_task.owner_key)
    try:
        task = await request.app.state.orchestrator.cancel(task_run_id=task_run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="task not found") from None
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return _build_task_response(task, context)
