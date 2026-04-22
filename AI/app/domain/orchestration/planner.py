from __future__ import annotations

from app.core.utils.ids import new_id
from app.domain.orchestration.contracts import Worker, build_orchestration_detail
from app.domain.tasks.models import StepRun, TaskRun
from app.domain.tasks.schemas import PlannedStep, PlannedTask
from app.domain.tasks.step_detail import build_default_step_detail, merge_step_detail


class Planner:
    """초기 step 과 handoff step 생성을 담당한다."""

    def create_initial_plan(
        self,
        *,
        route: str,
        worker: Worker,
        owner_key: str,
        input_payload: dict,
    ) -> PlannedTask:
        return PlannedTask(
            flow_name=route,
            task_type=worker.task_type,
            intent_type=worker.task_type,
            entry_capability=getattr(worker, "executor_key", route),
            owner_key=owner_key,
            title=getattr(worker, "task_title", worker.task_type),
            input_payload=input_payload,
            steps=[
                PlannedStep(
                    step_type=worker.step_type,
                    title=getattr(worker, "step_title", worker.step_type),
                    input_payload=input_payload,
                    detail_json=merge_step_detail(
                        build_default_step_detail(),
                        build_orchestration_detail(route=route),
                    ),
                )
            ],
        )

    def materialize_task(self, planned_task: PlannedTask) -> TaskRun:
        return TaskRun(
            task_run_id=new_id("task"),
            task_type=planned_task.task_type,
            flow_name=planned_task.flow_name,
            owner_key=planned_task.owner_key,
            status="PENDING",
            intent_type=planned_task.intent_type,
            entry_capability=planned_task.entry_capability,
            title=planned_task.title or planned_task.task_type,
            input_payload=planned_task.input_payload,
        )

    def materialize_initial_step(self, *, task: TaskRun, planned_task: PlannedTask) -> StepRun:
        first_step = planned_task.steps[0]
        return StepRun(
            step_run_id=new_id("step"),
            task_run_id=task.task_run_id,
            step_order=1,
            step_type=first_step.step_type,
            executor_key=planned_task.entry_capability,
            status="PENDING",
            title=first_step.title or first_step.step_type,
            input_payload=first_step.input_payload,
            detail_json=merge_step_detail(build_default_step_detail(), first_step.detail_json),
        )

    def create_handoff_step(
        self,
        *,
        task: TaskRun,
        route: str,
        worker: Worker,
        input_payload: dict,
        step_order: int,
    ) -> StepRun:
        return StepRun(
            step_run_id=new_id("step"),
            task_run_id=task.task_run_id,
            step_order=step_order,
            step_type=worker.step_type,
            executor_key=getattr(worker, "executor_key", route),
            status="PENDING",
            title=getattr(worker, "step_title", worker.step_type),
            input_payload=input_payload,
            detail_json=merge_step_detail(
                build_default_step_detail(),
                build_orchestration_detail(route=route),
            ),
        )
