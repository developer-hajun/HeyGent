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
    flow_name: str
    status: str
    title: str | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)
    result_payload: dict[str, Any] = Field(default_factory=dict)
    wait_payload: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    progress_summary: str | None = None
    revision: int
    created_at: datetime | None = None
    started_at: datetime | None = None
    updated_at: datetime | None = None
    ended_at: datetime | None = None


class TaskEventResponse(BaseModel):
    event_id: str
    event_type: str
    task_run_id: str
    step_run_id: str | None = None
    status: str | None = None
    summary_message: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: str
