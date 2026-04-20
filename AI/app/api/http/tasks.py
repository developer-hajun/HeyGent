from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.contracts.task.task_request import CreateTaskRequest, ResumeTaskRequest
from app.contracts.task.task_response import StepRunResponse, TaskEventResponse, TaskRunResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskRunResponse)
async def create_task(request: Request, payload: CreateTaskRequest) -> TaskRunResponse:
    orchestrator = request.app.state.orchestrator
    engine = request.app.state.task_engine
    try:
        task, step, flow = orchestrator.plan(
            flow_name=payload.flow_name,
            owner_key=payload.owner_key,
            input_payload=payload.input_payload,
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"unknown flow: {error.args[0]}") from error
    task = await engine.run(task=task, step=step, flow=flow)
    return TaskRunResponse.model_validate(task, from_attributes=True)


@router.get("/{task_run_id}", response_model=TaskRunResponse)
def get_task(request: Request, task_run_id: str) -> TaskRunResponse:
    task = request.app.state.repository.get_task(task_run_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return TaskRunResponse.model_validate(task, from_attributes=True)


@router.get("/{task_run_id}/steps", response_model=list[StepRunResponse])
def list_steps(request: Request, task_run_id: str) -> list[StepRunResponse]:
    steps = request.app.state.repository.list_steps(task_run_id)
    return [StepRunResponse.model_validate(step, from_attributes=True) for step in steps]


@router.get("/{task_run_id}/events", response_model=list[TaskEventResponse])
def list_events(request: Request, task_run_id: str) -> list[TaskEventResponse]:
    events = request.app.state.repository.list_events(task_run_id)
    return [TaskEventResponse.model_validate(event, from_attributes=True) for event in events]


@router.post("/{task_run_id}/resume", response_model=TaskRunResponse)
async def resume_task(request: Request, task_run_id: str, payload: ResumeTaskRequest) -> TaskRunResponse:
    repository = request.app.state.repository
    task = repository.get_task(task_run_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    approval = repository.get_open_approval(task_run_id)
    if approval is None:
        raise HTTPException(status_code=409, detail="no open approval")
    approval_id = payload.approval_id or approval["approval_id"]
    flow = request.app.state.orchestrator._flows[task.flow_name]
    task = await request.app.state.task_engine.resume(task=task, flow=flow, approval_id=approval_id, payload=payload.payload)
    return TaskRunResponse.model_validate(task, from_attributes=True)
