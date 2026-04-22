from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Awaitable, Callable

from app.domain.capabilities.children.linkage import (
    build_child_failed_detail,
    build_child_pending_detail,
    build_child_result_detail,
)
from app.domain.capabilities.children.specs.child_session import ChildSessionSpec
from app.domain.tasks.runtime import TaskRun


@dataclass(frozen=True, slots=True)
class ChildSessionLaunchResult:
    agent_id: str
    child_task_run_id: str
    status: str
    summary: str | None


class ChildSessionLauncher:
    """child runtime 의 최소 뼈대다.

    지금 단계에서는 실제 child 세션을 완전하게 실행하지 않더라도,
    부모 StepRun detail 이 어떤 linkage 키를 가져야 하는지는 먼저 고정해 둔다.
    이후 delegate 기능을 붙일 때도 같은 키를 계속 쓰게 만들려는 목적이다.
    """

    def __init__(self) -> None:
        self._start_child: Callable[..., Awaitable[TaskRun]] | None = None

    def bind_start(self, start_child: Callable[..., Awaitable[TaskRun]]) -> None:
        """child 실행은 capabilities 안에서 직접 새 loop 를 만들지 않고 기존 runner 를 재사용한다."""

        self._start_child = start_child

    def build_pending_detail(self, spec: ChildSessionSpec) -> dict:
        return build_child_pending_detail(agent_id=self._agent_id(spec))

    def build_failed_detail(self, spec: ChildSessionSpec, error_message: str) -> dict:
        return build_child_failed_detail(agent_id=self._agent_id(spec), error_message=error_message)

    def build_result_detail(self, spec: ChildSessionSpec, result: ChildSessionLaunchResult) -> dict:
        return build_child_result_detail(
            agent_id=result.agent_id,
            child_task_run_id=result.child_task_run_id,
            status=result.status,
            summary=result.summary,
        )

    async def launch(self, *, spec: ChildSessionSpec, owner_key: str, input_payload: dict) -> ChildSessionLaunchResult:
        """부모 step 에서 child TaskRun 을 실제로 시작한다.

        핵심 원칙은 parent 가 child 를 "내부 함수 호출"처럼 다루지 않는 것이다.
        child 도 별도 TaskRun/StepRun/Event 를 가지는 독립 세션이어야 하므로,
        기존 AgentLoopRunner.start 경로를 다시 호출해 child task 를 생성한다.
        """

        if self._start_child is None:
            raise RuntimeError("child session start callback is not bound")

        task = await self._start_child(
            owner_key=owner_key,
            input_payload=input_payload,
            intent_type=spec.child_intent_type,
            entry_capability=spec.child_entry_capability,
        )
        return ChildSessionLaunchResult(
            agent_id=self._agent_id(spec),
            child_task_run_id=task.task_run_id,
            status=task.status,
            summary=self._summarize_child_task(task, spec.summary_prompt),
        )

    @staticmethod
    def _agent_id(spec: ChildSessionSpec) -> str:
        return f"{spec.parent_step_run_id}:{spec.child_entry_capability}"

    @staticmethod
    def _summarize_child_task(task: TaskRun, summary_prompt: str | None) -> str | None:
        if task.progress_summary:
            return task.progress_summary
        if isinstance(task.result_payload.get("text"), str):
            return task.result_payload["text"]
        if task.result_payload:
            rendered = json.dumps(task.result_payload, ensure_ascii=False)
            if summary_prompt:
                return f"{summary_prompt}: {rendered}"
            return rendered
        return summary_prompt
