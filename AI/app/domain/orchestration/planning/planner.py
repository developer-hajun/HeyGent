from __future__ import annotations

from app.core.utils.ids import new_id
from app.domain.capabilities.tools.contracts import TaskCapabilityExecutor
from app.domain.orchestration.contracts import build_orchestration_detail
from app.domain.orchestration.planning.todo_state import build_initial_todo_state, build_todo_detail_patch
from app.domain.tasks.detail import build_default_step_detail, build_semantic_step_detail, merge_step_detail
from app.domain.tasks.runtime import StepRun, TaskRun


class Planner:
    """TaskRun / StepRun 의 semantic 골격을 만든다."""

    def materialize_task(self, *, owner_key: str, input_payload: dict, executor: TaskCapabilityExecutor) -> TaskRun:
        return TaskRun(
            task_run_id=new_id("task"),
            task_type=executor.spec.task_type,
            intent_type=executor.spec.intent_type,
            entry_capability=executor.spec.entry_capability,
            owner_key=owner_key,
            status="PENDING",
            title=executor.spec.task_title,
            input_payload=input_payload,
        )

    def materialize_step(self, *, task: TaskRun, executor: TaskCapabilityExecutor, input_payload: dict, step_order: int) -> StepRun:
        step = StepRun(
            step_run_id=new_id("step"),
            task_run_id=task.task_run_id,
            step_order=step_order,
            step_type=executor.spec.step_type,
            executor_key=executor.spec.executor_key,
            status="PENDING",
            title=executor.spec.step_title,
            input_payload=input_payload,
            detail_json=build_default_step_detail(),
        )
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_orchestration_detail(
                intent_type=task.intent_type or executor.spec.intent_type,
                entry_capability=task.entry_capability or executor.spec.entry_capability,
                executor_key=executor.spec.executor_key,
                semantic_step=executor.spec.step_title,
            ),
        )
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_semantic_step_detail(
                step_run_id=step.step_run_id,
                semantic_key=executor.spec.semantic_key or executor.spec.step_type,
                semantic_step=executor.spec.step_title,
                semantic_goal=executor.spec.semantic_goal or executor.spec.step_title,
                lifecycle="pending",
            ),
        )
        initial_todo_state = build_initial_todo_state(
            step_title=executor.spec.step_title,
            operation_templates=executor.spec.operation_templates,
        )
        step.detail_json = merge_step_detail(step.detail_json, build_todo_detail_patch(initial_todo_state))
        return step

    def materialize_resume_step(self, *, task: TaskRun, step: StepRun, executor: TaskCapabilityExecutor) -> StepRun:
        """resume 는 기존 StepRun 을 재사용하되 semantic metadata 가 비면 다시 채운다.

        StepRun 은 approval 와 waiting 의 operational anchor 이므로,
        재개 시에는 새 step 를 만들지 않고 정확히 같은 step 를 다시 RUNNING 으로 올린다.
        """

        step.executor_key = step.executor_key or executor.spec.executor_key
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_orchestration_detail(
                intent_type=task.intent_type or executor.spec.intent_type,
                entry_capability=task.entry_capability or executor.spec.entry_capability,
                executor_key=step.executor_key,
                semantic_step=step.title or executor.spec.step_title,
            ),
        )
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_semantic_step_detail(
                step_run_id=step.step_run_id,
                semantic_key=executor.spec.semantic_key or step.step_type,
                semantic_step=step.title or executor.spec.step_title,
                semantic_goal=executor.spec.semantic_goal or step.title or executor.spec.step_title,
                lifecycle="resuming",
            ),
        )
        return step
