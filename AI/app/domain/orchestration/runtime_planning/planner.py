from __future__ import annotations

from app.contracts.task.step_status import StepStatus
from app.core.utils.ids import new_id
from app.tools.contracts import TaskExecutor
from app.domain.orchestration.contracts import build_orchestration_detail
from app.domain.orchestration.runtime_planning.todo_state import TodoItem, build_initial_todo_state, build_task_todo_payload, build_todo_detail_patch
from app.domain.tasks.detail import build_default_step_detail, build_planning_detail, build_semantic_step_detail, merge_step_detail
from app.domain.tasks.models import StepRun, TaskRun


class Planner:
    """TaskRun / StepRun 의 semantic 골격을 만든다."""

    def materialize_task(self, *, owner_key: str, input_payload: dict, executor: TaskExecutor) -> TaskRun:
        initial_todo_state = build_initial_todo_state(
            step_title=executor.spec.step_title,
            operation_templates=executor.spec.operation_templates,
        )
        return TaskRun(
            task_run_id=new_id("task"),
            task_type=executor.spec.task_type,
            intent_type=executor.spec.intent_type,
            entry_executor_key=executor.spec.entry_executor_key,
            owner_key=owner_key,
            status="PENDING",
            title=executor.spec.task_title,
            input_payload=input_payload,
            todo_state=build_task_todo_payload(initial_todo_state),
        )

    def materialize_step(self, *, task: TaskRun, executor: TaskExecutor, input_payload: dict, step_order: int) -> StepRun:
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
                entry_executor_key=task.entry_executor_key or executor.spec.entry_executor_key,
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

    def materialize_todo_step(self, *, task: TaskRun, executor: TaskExecutor, todo_item: TodoItem, step_order: int) -> StepRun:
        step = StepRun(
            step_run_id=new_id("step"),
            task_run_id=task.task_run_id,
            step_order=step_order,
            step_type=executor.spec.step_type,
            executor_key=executor.spec.executor_key,
            status=StepStatus.PENDING,
            title=todo_item.title,
            input_payload={
                "todo_key": todo_item.key,
                "todo_title": todo_item.title,
                "todo_status": todo_item.status,
            },
            detail_json=build_default_step_detail(),
            summary_message=todo_item.title,
        )
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_orchestration_detail(
                intent_type=task.intent_type or executor.spec.intent_type,
                entry_executor_key=task.entry_executor_key or executor.spec.entry_executor_key,
                executor_key=executor.spec.executor_key,
                semantic_step=todo_item.title,
            ),
        )
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_semantic_step_detail(
                step_run_id=step.step_run_id,
                semantic_key=f"todo.{todo_item.key}",
                semantic_step=todo_item.title,
                semantic_goal=todo_item.title,
                lifecycle="pending",
            ),
        )
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_planning_detail(
                todo_items=[
                    {
                        "key": todo_item.key,
                        "title": todo_item.title,
                        "kind": todo_item.kind,
                        "status": todo_item.status,
                    }
                ],
                current_key=todo_item.key if todo_item.status in {"pending", "in_progress"} else None,
            ),
        )
        return step

    def materialize_resume_step(self, *, task: TaskRun, step: StepRun, executor: TaskExecutor) -> StepRun:
        """resume 는 기존 StepRun 을 재사용하되 semantic metadata 가 비면 다시 채운다.

        StepRun 은 approval 와 waiting 의 operational anchor 이므로,
        재개 시에는 새 step 를 만들지 않고 정확히 같은 step 를 다시 RUNNING 으로 올린다.
        """

        step.executor_key = step.executor_key or executor.spec.executor_key
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_orchestration_detail(
                intent_type=task.intent_type or executor.spec.intent_type,
                entry_executor_key=task.entry_executor_key or executor.spec.entry_executor_key,
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
