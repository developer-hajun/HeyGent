from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PendingApprovalResponse(BaseModel):
    approval_id: str
    step_run_id: str | None = None
    status: str
    reason: str | None = None
    tool_call_id: str | None = None
    tool_name: str | None = None
    requested_at: str | None = None
    can_approve: bool = False
    can_reject: bool = False


class StepRunResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    step_run_id: str
    task_run_id: str
    step_order: int
    step_type: str
    status: str
    executor_key: str | None = None
    title: str | None = None
    semantic: TaskRunFlowSemanticResponse | None = None
    is_current: bool = False
    is_projected: bool = False
    child_task_run_id: str | None = None
    child_task: TaskRunFlowChildTaskResponse | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)
    output_payload: dict[str, Any] = Field(default_factory=dict)
    wait_payload: dict[str, Any] = Field(default_factory=dict)
    pending_approval: PendingApprovalResponse | None = Field(default=None, alias="pendingApproval")
    # approval 은 UI가 wait/detail payload를 직접 해석하지 않도록 별도 view로도 노출한다.
    detail_json: dict[str, Any] = Field(default_factory=dict)
    summary_message: str | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None


class TaskRunResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    task_run_id: str
    task_type: str
    intent_type: str | None = None
    entry_executor_key: str | None = None
    session_key: str | None = None
    current_step_run_id: str | None = None
    status: str
    title: str | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)
    result_payload: dict[str, Any] = Field(default_factory=dict)
    todo_state: dict[str, Any] = Field(default_factory=dict)
    wait_payload: dict[str, Any] = Field(default_factory=dict)
    pending_approval: PendingApprovalResponse | None = Field(default=None, alias="pendingApproval")
    error_message: str | None = None
    progress_summary: str | None = None
    revision: int
    created_at: datetime | None = None
    started_at: datetime | None = None
    updated_at: datetime | None = None
    ended_at: datetime | None = None


class StepRunSummaryResponse(BaseModel):
    step_run_id: str
    step_order: int
    step_type: str
    status: str
    title: str | None = None
    summary_message: str | None = None
    updated_at: datetime | None = None


class TaskRunListItemResponse(BaseModel):
    task_run_id: str
    task_type: str
    intent_type: str | None = None
    entry_executor_key: str | None = None
    session_key: str | None = None
    status: str
    title: str | None = None
    input_summary: str | None = None
    step_count: int = 0
    progress_summary: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    current_step: StepRunSummaryResponse | None = None


class TaskRunListResponse(BaseModel):
    items: list[TaskRunListItemResponse] = Field(default_factory=list)
    page: int
    page_size: int
    total_count: int
    has_previous: bool
    has_next: bool
    status_filter: str


class TaskRunFlowSemanticResponse(BaseModel):
    key: str | None = None
    step: str | None = None
    goal: str | None = None
    status: str | None = None


class TaskRunFlowActivityResponse(BaseModel):
    event_type: str
    status: str | None = None
    summary_message: str | None = None
    occurred_at: str


class TaskRunFlowChildTaskResponse(BaseModel):
    task_run_id: str
    status: str | None = None
    summary: str | None = None
    agent_id: str | None = None


class TaskRunFlowNodeResponse(BaseModel):
    step_run_id: str
    step_order: int
    title: str | None = None
    status: str
    step_type: str
    executor_key: str | None = None
    semantic: TaskRunFlowSemanticResponse | None = None
    is_current: bool
    is_projected: bool
    child_task_run_id: str | None = None
    child_task: TaskRunFlowChildTaskResponse | None = None
    activity: list[TaskRunFlowActivityResponse] = Field(default_factory=list)


class TaskRunFlowEdgeResponse(BaseModel):
    from_step_run_id: str | None = None
    to_step_run_id: str | None = None
    to_task_run_id: str | None = None
    relation: str


class TaskRunFlowResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    task_run_id: str
    status: str
    title: str | None = None
    current_step_run_id: str | None = None
    entry_executor_key: str | None = None
    summary: str | None = None
    pending_approval: PendingApprovalResponse | None = Field(default=None, alias="pendingApproval")
    nodes: list[TaskRunFlowNodeResponse] = Field(default_factory=list)
    edges: list[TaskRunFlowEdgeResponse] = Field(default_factory=list)


class ActiveTaskRunCurrentStepResponse(BaseModel):
    step_run_id: str
    title: str | None = None
    status: str
    executor_key: str | None = None


class ActiveTaskRunListItemResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    task_run_id: str
    source: str
    session_key: str | None = None
    status: str
    title: str | None = None
    current_step_run_id: str | None = None
    current_step: ActiveTaskRunCurrentStepResponse | None = None
    updated_at: datetime | None = None
    wait_reason: str | None = None
    pending_approval: PendingApprovalResponse | None = Field(default=None, alias="pendingApproval")


class ActiveTaskRunListResponse(BaseModel):
    items: list[ActiveTaskRunListItemResponse] = Field(default_factory=list)
    total_count: int


class TaskEventResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event_id: str
    event_id_alias: str | None = Field(default=None, alias="eventId")
    event_type: str
    task_run_id: str
    step_run_id: str | None = None
    status: str | None = None
    summary_message: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: str
    sequence: int | None = None
