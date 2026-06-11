"""ProgressSinkMixin: progress_sink 콜러블 생성 및 모델 진행 상태 반영."""
from __future__ import annotations

from typing import Any

from app.domain.tasks.detail import merge_step_detail


class ProgressSinkMixin:
    """TaskEngine의 progress_sink 팩토리 및 model.progress 업데이트 담당."""

    def _build_progress_sink(self, *, task: Any, step: Any):
        current_step = step
        handler = self.tool_registry.resolve()

        async def sink(
            *,
            event_type: str,
            summary_message: str | None = None,
            payload: dict | None = None,
        ) -> None:
            nonlocal current_step
            payload = payload or {}
            if event_type == "model.progress.updated":
                updated_step = self._apply_model_progress_update(
                    task=task,
                    step=current_step,
                    payload=payload,
                    summary_message=summary_message,
                )
                if updated_step is not None:
                    current_step = updated_step
                    sink.current_step = current_step
                    self._touch_linked_work_run(task)
                    await self._emit(
                        "step.updated",
                        task,
                        current_step,
                        payload={"reason": "model.progress", **payload},
                        summary_message=current_step.summary_message,
                    )
                return
            observed_step = await self._materialize_progress_step(
                task=task,
                handler=handler,
                event_type=event_type,
                payload=payload,
            )
            if observed_step is not None:
                current_step = observed_step
                sink.current_step = current_step
            linked_work_payload = await self._ensure_skill_work_link(
                task=task, event_type=event_type, payload=payload
            )
            if linked_work_payload is not None:
                await self._emit("work.linked", task, current_step, payload=linked_work_payload)
            self._touch_linked_work_run(task)
            await self._emit(event_type, task, current_step, payload=payload, summary_message=summary_message)

        sink.current_step = current_step
        return sink

    def _apply_model_progress_update(
        self,
        *,
        task: Any,
        step: Any,
        payload: dict,
        summary_message: str | None,
    ) -> Any:
        """LLM 응답 envelope의 진행 상태를 현재 StepRun에 반영한다."""
        if step is None and task.current_step_run_id:
            step = self.repository.get_step(task.current_step_run_id)
        if step is None:
            return None
        update = payload.get("progressUpdate") if isinstance(payload.get("progressUpdate"), dict) else payload
        if not isinstance(update, dict):
            return None
        title = self._compact_progress_text(
            update.get("title") or update.get("step") or update.get("label"),
            max_length=80,
        )
        summary = self._compact_progress_text(
            summary_message or update.get("summary") or update.get("message") or update.get("statusMessage"),
            max_length=160,
        )
        if title:
            step.title = title
        if summary:
            step.summary_message = summary
        detail_patch = {
            "progressUpdate": {
                **dict(update),
                "turn": payload.get("turn"),
                "source": "assistant_response",
            }
        }
        step.detail_json = merge_step_detail(step.detail_json, detail_patch)
        self.repository.update_step(step)
        return step

    @staticmethod
    def _compact_progress_text(value: Any, *, max_length: int) -> str | None:
        if not isinstance(value, str):
            return None
        text = " ".join(value.split())
        if not text:
            return None
        return text[:max_length].rstrip()
