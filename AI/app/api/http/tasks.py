from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.deps.task_context import TaskContext, get_task_context
from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_request import CreateTaskRequest, ResumeTaskRequest
from app.contracts.task.task_response import (
    StepRunResponse,
    StepRunSummaryResponse,
    TaskEventResponse,
    TaskRunListItemResponse,
    TaskRunListResponse,
    TaskRunResponse,
)
from app.contracts.task.task_status import TaskStatus
from app.domain.orchestration.contracts import OrchestrationRequest
from app.domain.tasks.models import StepRun

router = APIRouter(prefix="/tasks", tags=["tasks"])

_ACTIVE_STEP_STATUSES = {status.value for status in (StepStatus.PENDING, StepStatus.RUNNING, StepStatus.WAITING, StepStatus.BLOCKED)}
_TASK_TITLE_FALLBACKS = {
    "model.generate": "모델 응답 생성",
    "notion.page.create": "Notion 페이지 생성",
    "notion.database.append": "Notion 데이터 추가",
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
        status=task.status,
        title=_display_task_title(task, input_summary=input_summary),
        input_summary=input_summary,
        step_count=len(steps),
        progress_summary=task.progress_summary,
        created_at=task.created_at,
        updated_at=task.updated_at,
        current_step=current_step_response,
    )


@router.get("", response_model=TaskRunListResponse)
def list_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=8, ge=1, le=20),
    status: str = Query(default="ALL"),
    context: TaskContext = Depends(get_task_context),
) -> TaskRunListResponse:
    status_filter = _normalize_task_status_filter(status)
    offset = (page - 1) * page_size
    tasks = context.repository.list_tasks(status=status_filter, limit=page_size, offset=offset)
    total_count = context.repository.count_tasks(status=status_filter)
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


@router.post("", response_model=TaskRunResponse)
async def create_task(request: Request, payload: CreateTaskRequest, context: TaskContext = Depends(get_task_context)) -> TaskRunResponse:
    orchestrator = request.app.state.orchestrator
    try:
        task = await orchestrator.start(
            OrchestrationRequest(
                owner_key=payload.owner_key,
                input_payload=payload.input_payload,
                intent_type=payload.intent_type,
                entry_executor_key=payload.entry_executor_key,
            )
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"unknown intent or executor: {error.args[0]}") from error
    return TaskRunResponse.model_validate(task, from_attributes=True)


@router.get("/{task_run_id}", response_model=TaskRunResponse)
def get_task(task_run_id: str, context: TaskContext = Depends(get_task_context)) -> TaskRunResponse:
    task = context.repository.get_task(task_run_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return TaskRunResponse.model_validate(task, from_attributes=True)


@router.get("/{task_run_id}/steps", response_model=list[StepRunResponse])
def list_steps(task_run_id: str, context: TaskContext = Depends(get_task_context)) -> list[StepRunResponse]:
    steps = context.repository.list_steps(task_run_id)
    return [StepRunResponse.model_validate(step, from_attributes=True) for step in steps]


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
    return TaskRunResponse.model_validate(task, from_attributes=True)
