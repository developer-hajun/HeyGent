from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class TaskRun:
    """TaskRun 상태 전체를 담는 최소 도메인 모델이다."""

    task_run_id: str
    task_type: str
    flow_name: str
    owner_key: str
    status: str
    input_payload: dict[str, Any] = field(default_factory=dict)
    result_payload: dict[str, Any] = field(default_factory=dict)
    wait_payload: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    progress_summary: str | None = None
    revision: int = 0
    created_at: datetime | None = None
    started_at: datetime | None = None
    updated_at: datetime | None = None
    ended_at: datetime | None = None


@dataclass(slots=True)
class StepRun:
    """StepRun 은 TaskRun 내부 단계 단위 실행 상태를 나타낸다."""

    step_run_id: str
    task_run_id: str
    step_order: int
    step_type: str
    status: str
    input_payload: dict[str, Any] = field(default_factory=dict)
    output_payload: dict[str, Any] = field(default_factory=dict)
    wait_payload: dict[str, Any] = field(default_factory=dict)
    summary_message: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
