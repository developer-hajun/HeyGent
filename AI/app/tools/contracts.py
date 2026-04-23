from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.domain.tasks.runtime.step_run import StepRun
    from app.domain.tasks.runtime.task_run import TaskRun


@dataclass(frozen=True, slots=True)
class OperationTemplate:
    """semantic step 안에 포함될 내부 operation 정의다."""

    key: str
    title: str
    kind: str


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
    semantic_key: str | None = None
    semantic_goal: str | None = None
    operation_templates: tuple[OperationTemplate, ...] = ()


class TaskCapabilityExecutor(Protocol):
    spec: CapabilitySpec

    def execute(
        self,
        *,
        task: TaskRun,
        step: StepRun,
        resume_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...
