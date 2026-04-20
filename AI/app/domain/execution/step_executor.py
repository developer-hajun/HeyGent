from __future__ import annotations

from typing import Any, Protocol

from app.domain.tasks.models import StepRun, TaskRun


class FlowHandler(Protocol):
    def execute(self, *, task: TaskRun, step: StepRun, resume_payload: dict[str, Any] | None = None) -> dict[str, Any]: ...


class StepExecutor:
    """개별 StepRun 실행을 flow 구현체에 위임한다."""

    def execute(self, *, handler: FlowHandler, task: TaskRun, step: StepRun, resume_payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return handler.execute(task=task, step=step, resume_payload=resume_payload)
