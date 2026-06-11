"""EventEmitMixin: task/step 이벤트 발행 및 todo 동기화."""
from __future__ import annotations

from typing import Any

from app.domain.orchestration.runtime_planning.todo_state import (
    parse_task_todo_payload,
)
from app.domain.tasks.detail import (
    build_planning_detail,
    merge_step_detail,
)
from app.domain.tasks.display_context import build_task_display_context
from app.domain.tasks.events import build_task_event


class EventEmitMixin:
    """TaskEngine의 이벤트 발행, step 진행 구체화, todo 동기화 담당."""

    async def _emit(
        self,
        event_type: str,
        task: Any,
        step: Any = None,
        payload: dict | None = None,
        summary_message: str | None = None,
    ) -> None:
        event_status = self._event_status(event_type=event_type, task=task, step=step)
        event_summary = (
            summary_message
            if summary_message is not None
            else self._event_summary(event_type=event_type, task=task, step=step)
        )
        event_payload = self._event_payload(event_type=event_type, step=step, payload=payload)
        event_payload["displayContext"] = build_task_display_context(task, step)
        event = build_task_event(
            event_type=event_type,
            task_run_id=task.task_run_id,
            step_run_id=step.step_run_id if step else None,
            producer="task_engine",
            status=event_status,
            summary_message=event_summary,
            payload=event_payload,
        )
        saved_event = self.repository.append_event(event)
        await self._event_broadcaster.publish(
            saved_event,
            event_type=event_type,
            task=task,
            step=step,
            status=event_status,
            summary_message=event_summary,
            payload=event_payload,
        )

    @staticmethod
    def _event_status(*, event_type: str, task: Any, step: Any = None) -> str:
        if step is not None and event_type.startswith("step."):
            return step.status
        if event_type.endswith(".completed"):
            return "COMPLETED"
        if event_type.endswith(".started"):
            return "RUNNING"
        if event_type.endswith(".failed"):
            return "FAILED"
        return task.status

    @staticmethod
    def _event_summary(*, event_type: str, task: Any, step: Any = None) -> str | None:
        if event_type.startswith("step.") and step is not None:
            return step.summary_message or step.title or step.step_type
        return task.progress_summary

    @staticmethod
    def _event_payload(*, event_type: str, step: Any = None, payload: dict | None = None) -> dict:
        event_payload = dict(payload or {})
        if step is not None and event_type.startswith("step."):
            event_payload.setdefault("step_run_id", step.step_run_id)
            event_payload.setdefault("stepRunId", step.step_run_id)
            event_payload.setdefault("step_title", step.title)
            event_payload.setdefault("stepTitle", step.title)
            event_payload.setdefault("step_order", step.step_order)
            event_payload.setdefault("stepOrder", step.step_order)
            semantic_detail = (step.detail_json or {}).get("semanticDetail") or {}
            semantic_step = semantic_detail.get("semanticStep")
            if isinstance(semantic_step, str) and semantic_step.strip():
                event_payload.setdefault("semantic_step", semantic_step)
                event_payload.setdefault("semanticStep", semantic_step)
        return event_payload

    async def _materialize_progress_step(
        self,
        *,
        task: Any,
        handler: Any,
        event_type: str,
        payload: dict,
    ) -> Any:
        """새 실행에서는 tool event가 StepRun을 만들지 않는다."""
        _ = (task, handler, event_type, payload)
        return None

    @staticmethod
    def _step_update_notifier(*, progress_sink: Any, task: Any):
        async def emit_step_update(
            *,
            step: Any,
            event_type: str,
            payload: dict,
            summary_message: str | None = None,
        ) -> None:
            if progress_sink is None:
                return
            progress_sink.current_step = step
            await progress_sink(event_type=event_type, summary_message=summary_message, payload=payload)

        return emit_step_update

    @staticmethod
    async def _notify_step_updated(
        callback: Any,
        *,
        step: Any,
        event_type: str,
        payload: dict,
        summary_message: str | None = None,
    ) -> None:
        if callback is None:
            return
        await callback(step=step, event_type=event_type, payload=payload, summary_message=summary_message)

    async def _sync_todo_steps(self, *, task: Any, handler: Any) -> None:
        todo_state = parse_task_todo_payload(task.todo_state)
        if not todo_state.items:
            return
        if not task.current_step_run_id:
            return

        current_step = self.repository.get_step(task.current_step_run_id)
        if current_step is None:
            return

        current_step.detail_json = merge_step_detail(
            current_step.detail_json,
            build_planning_detail(
                todo_items=[
                    {
                        "key": item.key,
                        "title": item.title,
                        "kind": item.kind,
                        "status": item.status,
                    }
                    for item in todo_state.items
                ],
                current_key=todo_state.current_key,
            ),
        )
        self.repository.update_step(current_step)
