from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.domain.tasks.runtime import StepRun, TaskRun


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


class TaskCapabilityExecutor(Protocol):
    spec: CapabilitySpec

    def execute(
        self,
        *,
        task: TaskRun,
        step: StepRun,
        resume_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...
