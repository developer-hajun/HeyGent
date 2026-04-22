from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.domain.tasks.runtime import StepRun, TaskRun


@dataclass(frozen=True, slots=True)
class OperationTemplate:
    """semantic step 안에 포함될 내부 operation 정의다.

    StepRun 하나가 사용자에게 보이는 큰 의미 단위라면,
    operation 은 그 안에서 실제로 어떤 하위 동작들이 수행되는지를 설명하는 더 작은 흔적이다.
    """

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
    # semantic_key 는 "이 step 을 사용자에게 어떤 의미 단위로 설명할 것인가"를 고정한다.
    # 지금은 capability 1회 실행이 step 1개와 거의 1:1 이지만,
    # 이후 한 step 안에 여러 tool/llm 호출을 묶더라도 이 키를 semantic 기준점으로 유지한다.
    semantic_key: str | None = None
    # semantic_goal 은 StepRun 이 왜 존재하는지 설명하는 한 줄 목적이다.
    # 단순 executor 이름이 아니라, 이 step 이 끝나면 사용자가 무엇을 얻는지를 남긴다.
    semantic_goal: str | None = None
    # operation_templates 는 이 semantic step 내부에 어떤 하위 동작들이 예정되어 있는지 설명한다.
    # planner 는 이 목록으로 초기 todo/operation 상태를 만들고,
    # 실행 결과는 같은 key 를 기준으로 어떤 하위 동작이 완료됐는지 갱신한다.
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
