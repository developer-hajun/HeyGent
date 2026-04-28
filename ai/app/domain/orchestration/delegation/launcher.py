from __future__ import annotations

from typing import Awaitable, Callable

from app.domain.orchestration.delegation.linkage import (
    build_child_failed_detail,
    build_child_pending_detail,
    build_child_result_detail,
)
from app.domain.orchestration.delegation.spec import ChildSessionLaunchResult, ChildSessionSpec
from app.domain.orchestration.delegation.summary import summarize_child_task
from app.domain.tasks.models import TaskRun


class ChildSessionLauncher:
    """Launch child TaskRuns through the same runner used by the parent loop."""

    def __init__(self) -> None:
        self._start_child: Callable[..., Awaitable[TaskRun]] | None = None

    def bind_start(self, start_child: Callable[..., Awaitable[TaskRun]]) -> None:
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

    async def launch(self, *, spec: ChildSessionSpec, owner_key: str, session_key: str | None, input_payload: dict) -> ChildSessionLaunchResult:
        if self._start_child is None:
            raise RuntimeError("child session start callback is not bound")

        task = await self._start_child(
            owner_key=owner_key,
            session_key=session_key,
            input_payload=input_payload,
            intent_type=spec.child_intent_type,
            entry_executor_key=spec.child_entry_executor_key,
        )
        return ChildSessionLaunchResult(
            agent_id=self._agent_id(spec),
            child_task_run_id=task.task_run_id,
            status=task.status,
            summary=summarize_child_task(task, spec.summary_prompt),
        )

    @staticmethod
    def _agent_id(spec: ChildSessionSpec) -> str:
        return f"{spec.parent_step_run_id}:{spec.child_entry_executor_key}"
