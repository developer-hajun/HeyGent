from __future__ import annotations

from app.domain.orchestration.runtime_planning.todo_state import apply_operation_results, build_todo_detail_patch
from app.domain.tasks.detail import build_operation_detail


class OutcomeInspector:
    """executor outcome 에서 StepRun detail 과 summary 를 보강한다."""

    def inspect(self, *, step, outcome: dict) -> dict:
        operations = list(outcome.get("operations") or [])
        detail_json = dict(outcome.get("detail_json") or {})
        summary_message = outcome.get("summary_message")

        if operations:
            detail_json = {
                **detail_json,
                **build_operation_detail(operations),
            }
            todo_state = apply_operation_results(step.detail_json, operations)
            detail_json = {
                **detail_json,
                **build_todo_detail_patch(todo_state),
            }
            summary_message = summary_message or self._build_operation_summary(operations)

        return {
            **outcome,
            "detail_json": detail_json,
            "summary_message": summary_message or step.summary_message or step.title or step.step_type,
        }

    @staticmethod
    def _build_operation_summary(operations: list[dict]) -> str:
        completed_titles = [str(operation.get("title")) for operation in operations if operation.get("status") == "completed"]
        if completed_titles:
            return ", ".join(completed_titles[:2])
        return "step operation updated"
