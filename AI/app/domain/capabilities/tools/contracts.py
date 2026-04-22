from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.domain.tasks.models import StepRun, TaskRun


@dataclass(slots=True)
class CapabilitySpec:
    """loop 가 실행자를 이해하는 데 필요한 최소 정적 정보다."""

    intent_type: str
    entry_capability: str
    executor_key: str
    task_type: str
    task_title: str
    step_type: str
    step_title: str


class TaskCapabilityExecutor(Protocol):
    spec: CapabilitySpec

    def execute(
        self,
        *,
        task: TaskRun,
        step: StepRun,
        resume_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...
