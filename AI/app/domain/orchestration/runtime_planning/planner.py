from __future__ import annotations

from app.contracts.task.step_status import StepStatus
from app.core.utils.ids import new_id
from app.tools.contracts import TaskExecutor
from app.domain.orchestration.contracts import build_orchestration_detail
from app.domain.orchestration.runtime_planning.task_plan import TaskPlanStep, build_task_plan, build_task_plan_todo_state
from app.domain.orchestration.runtime_planning.todo_state import TodoItem, TodoState, build_initial_todo_state, build_task_todo_payload, build_todo_detail_patch
from app.domain.tasks.detail import build_default_step_detail, build_planning_detail, build_semantic_step_detail, merge_step_detail
from app.domain.tasks.models import StepRun, TaskRun


class Planner:
    """TaskRun / StepRun의 semantic(사용자에게 보이는 의미 단계) 골격을 만든다."""

    def materialize_task(self, *, owner_key: str, session_key: str | None, input_payload: dict, executor: TaskExecutor) -> TaskRun:
        task_plan = build_task_plan(input_payload=input_payload, default_task_title=executor.spec.task_title)
        # agent.loop는 native tool call(모델이 구조화된 도구 호출을 직접 반환하는 방식)을 보고
        # 실행 중 todo projection(todo 상태를 화면/상태 detail로 투영한 값)을 갱신한다.
        # 그래서 명시적 task_plan이 없으면 고정 operation todo(미리 박아 둔 실행 단계 목록)를 만들지 않는다.
        initial_todo_state = (
            build_task_plan_todo_state(task_plan)
            if task_plan is not None
            else TodoState(items=(), current_key=None)
            if executor.spec.executor_key == "agent.loop"
            else build_initial_todo_state(
                step_title=executor.spec.step_title,
                operation_templates=executor.spec.operation_templates,
            )
        )
        return TaskRun(
            task_run_id=new_id("task"),
            task_type=executor.spec.task_type,
            intent_type=executor.spec.intent_type,
            entry_executor_key=executor.spec.entry_executor_key,
            owner_key=owner_key,
            session_key=session_key,
            status="PENDING",
            title=task_plan.title if task_plan is not None and task_plan.title else executor.spec.task_title,
            input_payload=input_payload,
            todo_state=build_task_todo_payload(initial_todo_state),
        )

    def materialize_step(self, *, task: TaskRun, executor: TaskExecutor, input_payload: dict, step_order: int) -> StepRun:
        task_plan = build_task_plan(input_payload=input_payload, default_task_title=executor.spec.task_title)
        current_step_title = task_plan.current_step.title if task_plan is not None else executor.spec.step_title
        current_semantic_key = (
            task_plan.current_step.semantic_key if task_plan is not None else self._executor_semantic_key(executor)
        )
        current_semantic_goal = (
            task_plan.current_step.goal if task_plan is not None else executor.spec.semantic_goal or executor.spec.step_title
        )
        step = StepRun(
            step_run_id=new_id("step"),
            task_run_id=task.task_run_id,
            step_order=step_order,
            step_type=executor.spec.step_type,
            executor_key=executor.spec.executor_key,
            status="PENDING",
            title=current_step_title,
            input_payload=input_payload,
            detail_json=build_default_step_detail(),
        )
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_orchestration_detail(
                intent_type=task.intent_type or executor.spec.intent_type,
                entry_executor_key=task.entry_executor_key or executor.spec.entry_executor_key,
                executor_key=executor.spec.executor_key,
                semantic_step=current_step_title,
            ),
        )
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_semantic_step_detail(
                step_run_id=step.step_run_id,
                semantic_key=current_semantic_key,
                semantic_step=current_step_title,
                semantic_goal=current_semantic_goal,
                lifecycle="pending",
            ),
        )
        initial_todo_state = build_initial_todo_state(
            step_title=current_step_title,
            operation_templates=executor.spec.operation_templates,
        )
        step.detail_json = merge_step_detail(step.detail_json, build_todo_detail_patch(initial_todo_state))
        return step

    def materialize_observed_step(
        self,
        *,
        task: TaskRun,
        executor: TaskExecutor,
        input_payload: dict,
        step_order: int,
        outcome: dict,
    ) -> StepRun:
        """첫 모델 응답을 본 뒤 StepRun(사용자에게 보이는 의미 단계)을 만든다.

        agent.loop는 실행 전에 의미 단계를 확정하기 어려울 수 있어, outcome의 detail_json을
        우선 신뢰하고 부족한 값만 executor 기본값으로 보강한다.
        """

        detail_json = merge_step_detail(build_default_step_detail(), outcome.get("detail_json"))
        semantic_detail = detail_json.get("semanticDetail") or {}
        title = (
            semantic_detail.get("semanticStep")
            or outcome.get("summary_message")
            or executor.spec.step_title
        )
        goal = semantic_detail.get("goal") or executor.spec.semantic_goal or title
        step = StepRun(
            step_run_id=new_id("step"),
            task_run_id=task.task_run_id,
            step_order=step_order,
            step_type=executor.spec.step_type,
            executor_key=executor.spec.executor_key,
            status=StepStatus.PENDING,
            title=str(title),
            input_payload=input_payload,
            detail_json=detail_json,
            summary_message=outcome.get("summary_message"),
        )
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_orchestration_detail(
                intent_type=task.intent_type or executor.spec.intent_type,
                entry_executor_key=task.entry_executor_key or executor.spec.entry_executor_key,
                executor_key=executor.spec.executor_key,
                semantic_step=str(title),
            ),
        )
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_semantic_step_detail(
                step_run_id=step.step_run_id,
                semantic_key=semantic_detail.get("semanticKey") or self._executor_semantic_key(executor),
                semantic_step=str(title),
                semantic_goal=str(goal),
                lifecycle="running",
            ),
        )
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
                semantic_key=self._todo_semantic_key(todo_item),
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
        """resume는 기존 StepRun을 재사용하되 semantic metadata가 비면 다시 채운다.

        StepRun은 approval과 waiting의 operational anchor(실행 이력을 묶는 기준점)이므로,
        재개 시에는 새 step을 만들지 않고 정확히 같은 step을 다시 RUNNING으로 올린다.
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
                semantic_key=self._executor_semantic_key(executor, fallback=step.step_type),
                semantic_step=step.title or executor.spec.step_title,
                semantic_goal=executor.spec.semantic_goal or step.title or executor.spec.step_title,
                lifecycle="resuming",
            ),
        )
        return step

    def materialize_handoff_step(
        self,
        *,
        task: TaskRun,
        step: StepRun,
        executor: TaskExecutor,
        plan_step: TaskPlanStep,
        input_payload: dict,
    ) -> StepRun:
        """다음 workflow 단계로 넘어갈 때 projected step(계획에서 미리 만들어 둔 단계)을 실행 anchor(실행 이력을 묶는 기준점)로 승격한다."""

        step.step_type = executor.spec.step_type
        step.executor_key = executor.spec.executor_key
        step.title = plan_step.title
        step.input_payload = {
            **step.input_payload,
            **input_payload,
            "todo_key": plan_step.key,
            "todo_title": plan_step.title,
        }
        step.summary_message = plan_step.title
        step.detail_json = merge_step_detail(
            build_default_step_detail(),
            build_orchestration_detail(
                intent_type=task.intent_type or executor.spec.intent_type,
                entry_executor_key=task.entry_executor_key or executor.spec.entry_executor_key,
                executor_key=executor.spec.executor_key,
                semantic_step=plan_step.title,
            ),
        )
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_semantic_step_detail(
                step_run_id=step.step_run_id,
                semantic_key=plan_step.semantic_key,
                semantic_step=plan_step.title,
                semantic_goal=plan_step.goal,
                lifecycle="pending",
            ),
        )
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_todo_detail_patch(
                build_initial_todo_state(
                    step_title=plan_step.title,
                    operation_templates=executor.spec.operation_templates,
                )
            ),
        )
        return step

    @staticmethod
    def _executor_semantic_key(executor: TaskExecutor, *, fallback: str | None = None) -> str:
        """executor 기본 semanticKey 생성 규칙.

        StepRun은 내부 operation이 아니라 의미 단위 anchor(사용자에게 보이는 단계 기준점)이므로,
        executor가 명시한 semantic_key를 우선 사용하고, fallback이 있으면 그 값을 쓰며,
        둘 다 없으면 step_type을 기준 semanticKey로 고정한다.
        """

        return executor.spec.semantic_key or fallback or executor.spec.step_type

    @staticmethod
    def _todo_semantic_key(todo_item: TodoItem) -> str:
        """todo projection(실행 중 todo 상태를 화면 단계로 투영한 값)은 사용자에게 별도 단계로 보이는 독립 semantic step이다."""

        return f"todo.{todo_item.key}"
