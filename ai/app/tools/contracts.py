from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.domain.tasks.models.step_run import StepRun
    from app.domain.tasks.models.task_run import TaskRun


@dataclass(frozen=True, slots=True)
class OperationTemplate:
    """semantic step 안에 포함될 내부 operation 정의다."""

    key: str
    title: str
    # kind 는 executor 별 자유 문자열이 아니라 공통 의미 집합을 따르는 편이 좋다.
    # 권장 값:
    # - prepare
    # - execute
    # - summarize
    # - handoff
    # - finalize
    kind: str


@dataclass(slots=True)
class ExecutorSpec:
    """loop 가 실행자를 이해하는 데 필요한 최소 정적 정보다."""

    intent_type: str
    entry_executor_key: str
    executor_key: str
    task_type: str
    task_title: str
    step_type: str
    step_title: str
    semantic_key: str | None = None
    semantic_goal: str | None = None
    operation_templates: tuple[OperationTemplate, ...] = ()


class TaskExecutor(Protocol):
    spec: ExecutorSpec

    def execute(
        self,
        *,
        task: TaskRun,
        step: StepRun | None,
        resume_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...
