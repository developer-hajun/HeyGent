from __future__ import annotations

from app.contracts.task.task_status import TaskStatus
from app.domain.orchestration.contracts import InspectionResult, ORCHESTRATION_DETAIL_KEY
from app.domain.tasks.models import StepRun, TaskRun


class ResultInspector:
    """worker 실행 결과를 next action 으로 해석한다."""

    def inspect(self, *, task: TaskRun, step: StepRun) -> InspectionResult:
        orchestration = (step.detail_json or {}).get(ORCHESTRATION_DETAIL_KEY, {})
        next_action = orchestration.get("nextAction")
        handoff_to = orchestration.get("handoffTo")
        followup_question = orchestration.get("followupQuestion")

        if next_action == "handoff":
            return InspectionResult(
                next_action="handoff",
                handoff_to=handoff_to,
                next_input_payload=self._build_handoff_input(task, step),
            )

        if task.status == TaskStatus.WAITING:
            return InspectionResult(
                next_action="ask_user",
                followup_question=followup_question or self._extract_followup_question(task, step),
            )

        if task.status == TaskStatus.COMPLETED:
            return InspectionResult(next_action="done")

        if task.status == TaskStatus.FAILED:
            return InspectionResult(next_action="fail")

        return InspectionResult(next_action="fail")

    def _extract_followup_question(self, task: TaskRun, step: StepRun) -> str | None:
        wait_payload = step.wait_payload or task.wait_payload or {}
        question = wait_payload.get("followup_question")
        if isinstance(question, str) and question.strip():
            return question
        return None

    def _build_handoff_input(self, task: TaskRun, step: StepRun) -> dict:
        return {
            "previous_step_output": step.output_payload,
            "task_result": task.result_payload,
            "original_input": task.input_payload,
        }
