from __future__ import annotations

from app.core.utils.ids import new_id
from app.domain.tasks.models import StepRun, TaskRun
from app.domain.tasks.schemas import PlannedStep, PlannedTask
from app.domain.tasks.step_detail import build_default_step_detail, merge_step_detail


class Planner:
    """Flow 정의를 TaskRun/StepRun 계획으로 바꾼다."""

    def create_task_plan(
        self,
        *,
        flow_name: str,
        task_type: str,
        owner_key: str,
        input_payload: dict,
        step_type: str,
        task_title: str | None = None,
        step_title: str | None = None,
        step_detail: dict | None = None,
    ) -> PlannedTask:
        # 현재 단계는 단일 step 플로우를 기본값으로 유지한다.
        return PlannedTask(
            flow_name=flow_name,
            task_type=task_type,
            owner_key=owner_key,
            title=task_title,
            input_payload=input_payload,
            steps=[
                PlannedStep(
                    step_type=step_type,
                    title=step_title,
                    input_payload=input_payload,
                    detail_json=merge_step_detail(build_default_step_detail(), step_detail or {}),
                )
            ],
        )

    def materialize(self, planned_task: PlannedTask) -> tuple[TaskRun, StepRun]:
        task = TaskRun(
            task_run_id=new_id("task"),
            task_type=planned_task.task_type,
            flow_name=planned_task.flow_name,
            owner_key=planned_task.owner_key,
            status="PENDING",
            title=planned_task.title or planned_task.task_type,
            input_payload=planned_task.input_payload,
        )
        first_step = planned_task.steps[0]
        step = StepRun(
            step_run_id=new_id("step"),
            task_run_id=task.task_run_id,
            step_order=1,
            step_type=first_step.step_type,
            status="PENDING",
            title=first_step.title or first_step.step_type,
            input_payload=first_step.input_payload,
            detail_json=merge_step_detail(build_default_step_detail(), first_step.detail_json),
        )
        return task, step
