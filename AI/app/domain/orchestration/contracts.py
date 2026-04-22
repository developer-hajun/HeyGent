from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from app.domain.tasks.models import StepRun, TaskRun

NextAction = Literal["done", "ask_user", "handoff", "fail"]
ORCHESTRATION_DETAIL_KEY = "orchestration"


@dataclass(slots=True)
class OrchestrationRequest:
    """오케스트레이터 시작 입력을 한 곳으로 모은다."""

    owner_key: str
    input_payload: dict[str, Any]
    requested_route: str | None = None


@dataclass(slots=True)
class InspectionResult:
    """worker 실행 결과를 main orchestrator 분기 값으로 정규화한다."""

    next_action: NextAction
    handoff_to: str | None = None
    followup_question: str | None = None
    next_input_payload: dict[str, Any] = field(default_factory=dict)


class Worker(Protocol):
    flow_name: str
    task_type: str
    step_type: str
    task_title: str
    step_title: str

    def execute(
        self,
        *,
        task: TaskRun,
        step: StepRun,
        resume_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


def build_orchestration_detail(
    *,
    route: str,
    next_action: NextAction = "done",
    handoff_to: str | None = None,
    followup_question: str | None = None,
) -> dict[str, Any]:
    return {
        ORCHESTRATION_DETAIL_KEY: {
            "activeRoute": route,
            "nextAction": next_action,
            "handoffTo": handoff_to,
            "followupQuestion": followup_question,
        }
    }
