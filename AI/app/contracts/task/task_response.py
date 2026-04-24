from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class StepRunResponse(BaseModel):
    step_run_id: str
    task_run_id: str
    step_order: int
    step_type: str
    status: str
    executor_key: str | None = None
    title: str | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)
    output_payload: dict[str, Any] = Field(default_factory=dict)
    wait_payload: dict[str, Any] = Field(default_factory=dict)
    detail_json: dict[str, Any] = Field(default_factory=dict)
    summary_message: str | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None


class TaskRunResponse(BaseModel):
    task_run_id: str
    task_type: str
    intent_type: str | None = None
    entry_executor_key: str | None = None
    current_step_run_id: str | None = None
    status: str
    title: str | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)
    result_payload: dict[str, Any] = Field(default_factory=dict)
    todo_state: dict[str, Any] = Field(default_factory=dict)
    wait_payload: dict[str, Any] = Field(default_factory=dict)
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


class TaskEventResponse(BaseModel):
    event_id: str
    event_type: str
    task_run_id: str
    step_run_id: str | None = None
    status: str | None = None
    summary_message: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: str
