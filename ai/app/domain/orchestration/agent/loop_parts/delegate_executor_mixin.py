"""DelegateExecutorMixin: delegate_task 실행 팩토리."""
from __future__ import annotations

from typing import Any

from app.contracts.task.step_status import StepStatus
from app.core.time import utc_now


class DelegateExecutorMixin:
    """TaskEngine의 delegate_task 실행 팩토리 담당."""

    def _build_delegate_executor(self, *, task: Any, handler: Any, progress_sink: Any):
        async def execute_delegate(
            *,
            child_session: dict,
            tool_call_id: str,
            args: dict,
            accepted_result: dict,
        ) -> dict:
            step = getattr(progress_sink, "current_step", None)
            if step is None and task.current_step_run_id:
                step = self.repository.get_step(task.current_step_run_id)
            if step is None:
                return {
                    "ok": False,
                    "content": "delegate_task 실행에 필요한 현재 StepRun 실행 anchor가 없습니다.",
                    "error": {
                        "code": "runtime_step_required_before_delegate",
                        "message": "delegate_task requires an active runtime-owned StepRun.",
                    },
                    "child_session": child_session,
                }
            elif step.status == StepStatus.PENDING:
                step.status = StepStatus.RUNNING
                step.started_at = step.started_at or task.started_at or utc_now()
                task.current_step_run_id = step.step_run_id
                self.repository.update_task(task)
                self.repository.update_step(step)
                progress_sink.current_step = step
                await self._emit("step.started", task, step)

            async def emit_step_update(
                *,
                step: Any,
                event_type: str,
                payload: dict,
                summary_message: str | None = None,
            ) -> None:
                progress_sink.current_step = step
                await self._emit(event_type, task, step, payload=payload, summary_message=summary_message)

            return await self.delegate_runtime.run_child_as_tool(
                task=task,
                step=step,
                child_session=child_session,
                repository=self.repository,
                on_step_updated=emit_step_update,
            )

        return execute_delegate
