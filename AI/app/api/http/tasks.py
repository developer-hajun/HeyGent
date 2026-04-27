from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request

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
    TaskRunFlowChildTaskResponse,
    TaskRunFlowEdgeResponse,
    TaskRunFlowNodeResponse,
    TaskRunFlowResponse,
    TaskRunFlowSemanticResponse,
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
        child_task = None
        child_task_run_id = str(agent_detail.get("childTaskRunId") or "").strip() or None
        if child_task_run_id is not None:
            child_task = TaskRunFlowChildTaskResponse(
                task_run_id=child_task_run_id,
                status=agent_detail.get("status"),
                summary=agent_detail.get("summary"),
                agent_id=agent_detail.get("agentId"),
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
                child_task_run_id=child_task_run_id,
                child_task=child_task,
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
    child_task = None
    child_task_run_id = str(agent_detail.get("childTaskRunId") or "").strip() or None
    if child_task_run_id is not None:
        child_task = TaskRunFlowChildTaskResponse(
            task_run_id=child_task_run_id,
            status=agent_detail.get("status"),
            summary=agent_detail.get("summary"),
            agent_id=agent_detail.get("agentId"),
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
        child_task_run_id=child_task_run_id,
        child_task=child_task,
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
        child_task_run_id = str((((step.detail_json or {}).get("agentDetail") or {}).get("childTaskRunId")) or "").strip()
        if not child_task_run_id:
            continue
        edges.append(
            TaskRunFlowEdgeResponse(
                from_step_run_id=step.step_run_id,
                to_task_run_id=child_task_run_id,
                relation="delegates_to",
            )
        )
    return edges


@router.get("", response_model=TaskRunListResponse)
def list_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=8, ge=1, le=20),
    status: str = Query(default="ALL"),
    session_key: str | None = Query(default=None, alias="sessionKey"),
    context: TaskContext = Depends(get_task_context),
) -> TaskRunListResponse:
    status_filter = _normalize_task_status_filter(status)
    offset = (page - 1) * page_size
    tasks = context.repository.list_tasks(status=status_filter, session_key=session_key, limit=page_size, offset=offset)
    total_count = context.repository.count_tasks(status=status_filter, session_key=session_key)
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
def list_active_tasks(
    session_key: str | None = Query(default=None, alias="sessionKey"),
    context: TaskContext = Depends(get_task_context),
) -> ActiveTaskRunListResponse:
    now = utc_now()
    active_total_count = context.repository.count_tasks_by_statuses(_ACTIVE_TASK_STATUSES, session_key=session_key)
    active_tasks = context.repository.list_tasks_by_statuses(_ACTIVE_TASK_STATUSES, session_key=session_key, limit=max(active_total_count, 1), offset=0)

    recent_total_pool = context.repository.count_tasks_by_statuses(_RECENT_TERMINAL_TASK_STATUSES, session_key=session_key)
    recent_candidates = context.repository.list_tasks_by_statuses(
        _RECENT_TERMINAL_TASK_STATUSES,
        session_key=session_key,
        limit=max(recent_total_pool, 1),
        offset=0,
    )

    items_by_task_run_id: dict[str, ActiveTaskRunListItemResponse] = {}
    for task in active_tasks:
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
    return ActiveTaskRunListResponse(
        items=items,
        total_count=len(items),
    )


@router.post("", response_model=TaskRunResponse)
async def create_task(request: Request, payload: CreateTaskRequest, context: TaskContext = Depends(get_task_context)) -> TaskRunResponse:
    orchestrator = request.app.state.orchestrator
    try:
        task = await orchestrator.start(
            OrchestrationRequest(
                owner_key=payload.owner_key,
                session_key=payload.session_key,
                input_payload=payload.input_payload,
                intent_type=payload.intent_type,
                entry_executor_key=payload.entry_executor_key,
            )
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"unknown intent or executor: {error.args[0]}") from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return _build_task_response(task, context)


@router.get("/{task_run_id}/flow", response_model=TaskRunFlowResponse)
def get_task_flow(task_run_id: str, context: TaskContext = Depends(get_task_context)) -> TaskRunFlowResponse:
    task = context.repository.get_task(task_run_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
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
def get_task(task_run_id: str, context: TaskContext = Depends(get_task_context)) -> TaskRunResponse:
    task = context.repository.get_task(task_run_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return _build_task_response(task, context)


@router.get("/{task_run_id}/steps", response_model=list[StepRunResponse])
def list_steps(task_run_id: str, context: TaskContext = Depends(get_task_context)) -> list[StepRunResponse]:
    task = context.repository.get_task(task_run_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
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
def list_events(task_run_id: str, context: TaskContext = Depends(get_task_context)) -> list[TaskEventResponse]:
    events = context.repository.list_events(task_run_id)
    return [TaskEventResponse.model_validate(event, from_attributes=True) for event in events]


@router.post("/{task_run_id}/resume", response_model=TaskRunResponse)
async def resume_task(request: Request, task_run_id: str, payload: ResumeTaskRequest, context: TaskContext = Depends(get_task_context)) -> TaskRunResponse:
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
    try:
        task = await request.app.state.orchestrator.cancel(task_run_id=task_run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="task not found") from None
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return _build_task_response(task, context)
