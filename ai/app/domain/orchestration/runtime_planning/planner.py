from __future__ import annotations

from app.contracts.task.step_status import StepStatus
from app.core.utils.ids import new_id
from app.tools.contracts import TaskHandler
from app.domain.orchestration.contracts import build_orchestration_detail
from app.domain.orchestration.runtime_planning.task_plan import TaskPlanStep, build_task_plan, build_task_plan_todo_state
from app.domain.orchestration.runtime_planning.todo_state import TodoState, build_initial_todo_state, build_task_todo_payload, build_todo_detail_patch
from app.domain.tasks.detail import build_default_step_detail, build_semantic_step_detail, merge_step_detail
from app.domain.tasks.models import StepRun, TaskRun


class Planner:
    """TaskRun / StepRun의 semantic(사용자에게 보이는 의미 단계) 골격을 만든다."""

    def materialize_task(self, *, owner_key: str, session_key: str | None, input_payload: dict, handler: TaskHandler) -> TaskRun:
        task_plan = build_task_plan(input_payload=input_payload, default_task_title=handler.spec.task_title)
        # agent.loop는 native tool call(모델이 구조화된 도구 호출을 직접 반환하는 방식)을 보고
        # 실행 중 todo projection(todo 상태를 화면/상태 detail로 투영한 값)을 갱신한다.
        # 그래서 명시적 task_plan이 없으면 고정 operation todo(미리 박아 둔 실행 단계 목록)를 만들지 않는다.
        initial_todo_state = (
            build_task_plan_todo_state(task_plan)
            if task_plan is not None
            else TodoState(items=(), current_key=None)
            if handler.spec.handler_key == "agent.loop"
            else build_initial_todo_state(
                step_title=handler.spec.step_title,
                operation_templates=handler.spec.operation_templates,
            )
        )
        return TaskRun(
            task_run_id=new_id("task"),
            task_type=handler.spec.task_type,
            intent_type=handler.spec.intent_type,
            entry_handler_key=handler.spec.entry_handler_key,
            owner_key=owner_key,
            session_key=session_key,
            status="PENDING",
            title=task_plan.title if task_plan is not None and task_plan.title else handler.spec.task_title,
            input_payload=input_payload,
            todo_state=build_task_todo_payload(initial_todo_state),
        )

    def materialize_step(self, *, task: TaskRun, handler: TaskHandler, input_payload: dict, step_order: int) -> StepRun:
        task_plan = build_task_plan(input_payload=input_payload, default_task_title=handler.spec.task_title)
        current_step_title = task_plan.current_step.title if task_plan is not None else handler.spec.step_title
        current_semantic_key = (
            task_plan.current_step.semantic_key if task_plan is not None else self._handler_semantic_key(handler)
        )
        current_semantic_goal = (
            task_plan.current_step.goal if task_plan is not None else handler.spec.semantic_goal or handler.spec.step_title
        )
        anchored_input_payload = self._with_plan_step_anchor(input_payload, task_plan.current_step) if task_plan is not None else input_payload
        step = StepRun(
            step_run_id=new_id("step"),
            task_run_id=task.task_run_id,
            step_order=step_order,
            step_type=handler.spec.step_type,
            handler_key=handler.spec.handler_key,
            status="PENDING",
            title=current_step_title,
            input_payload=anchored_input_payload,
            detail_json=build_default_step_detail(),
        )
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_orchestration_detail(
                intent_type=task.intent_type or handler.spec.intent_type,
                entry_handler_key=task.entry_handler_key or handler.spec.entry_handler_key,
                handler_key=handler.spec.handler_key,
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
            operation_templates=handler.spec.operation_templates,
        )
        step.detail_json = merge_step_detail(step.detail_json, build_todo_detail_patch(initial_todo_state))
        return step

    def materialize_observed_step(
        self,
        *,
        task: TaskRun,
        handler: TaskHandler,
        input_payload: dict,
        step_order: int,
        outcome: dict,
    ) -> StepRun:
        """첫 모델 응답을 본 뒤 StepRun(사용자에게 보이는 의미 단계)을 만든다.

        agent.loop는 실행 전에 의미 단계를 확정하기 어려울 수 있어, outcome의 detail_json을
        우선 신뢰하고 부족한 값만 handler 기본값으로 보강한다.
        """

        task_plan = build_task_plan(input_payload=input_payload, default_task_title=handler.spec.task_title)
        plan_step = task_plan.current_step if task_plan is not None else None
        detail_json = merge_step_detail(build_default_step_detail(), outcome.get("detail_json"))
        semantic_detail = detail_json.get("semanticDetail") or {}
        title = (
            plan_step.title
            if plan_step is not None
            else semantic_detail.get("semanticStep")
            or outcome.get("summary_message")
            or handler.spec.step_title
        )
        goal = plan_step.goal if plan_step is not None else semantic_detail.get("goal") or handler.spec.semantic_goal or title
        semantic_key = (
            plan_step.semantic_key
            if plan_step is not None
            else semantic_detail.get("semanticKey") or self._handler_semantic_key(handler)
        )
        step = StepRun(
            step_run_id=new_id("step"),
            task_run_id=task.task_run_id,
            step_order=step_order,
            step_type=handler.spec.step_type,
            handler_key=handler.spec.handler_key,
            status=StepStatus.PENDING,
            title=str(title),
            input_payload=self._with_plan_step_anchor(input_payload, plan_step) if plan_step is not None else input_payload,
            detail_json=detail_json,
            summary_message=outcome.get("summary_message"),
        )
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_orchestration_detail(
                intent_type=task.intent_type or handler.spec.intent_type,
                entry_handler_key=task.entry_handler_key or handler.spec.entry_handler_key,
                handler_key=handler.spec.handler_key,
                semantic_step=str(title),
            ),
        )
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_semantic_step_detail(
                step_run_id=step.step_run_id,
                semantic_key=semantic_key,
                semantic_step=str(title),
                semantic_goal=str(goal),
                lifecycle="running",
            ),
        )
        return step

    def materialize_observed_semantic_step(
        self,
        *,
        task: TaskRun,
        handler: TaskHandler,
        input_payload: dict,
        step_order: int,
        observed_step: dict,
        outcome: dict,
        include_outcome_detail: bool,
    ) -> StepRun:
        """모델이 선언한 의미 단계 하나를 StepRun으로 만든다.

        todo는 단계 내부 체크리스트이고, 이 메서드는 `step` planning tool로 모델이 직접
        선언한 큰 의미 단계에만 사용한다.
        """

        title = str(observed_step.get("title") or observed_step.get("summary") or handler.spec.step_title)
        summary = str(observed_step.get("summary") or title)
        goal = str(observed_step.get("goal") or summary or title)
        step_key = str(observed_step.get("id") or step_order).strip() or str(step_order)
        semantic_key = f"observed.{step_key}"
        detail_json = build_default_step_detail()
        if include_outcome_detail:
            detail_json = merge_step_detail(detail_json, outcome.get("detail_json"))
        step = StepRun(
            step_run_id=new_id("step"),
            task_run_id=task.task_run_id,
            step_order=step_order,
            step_type=handler.spec.step_type,
            handler_key=handler.spec.handler_key,
            status=StepStatus.PENDING,
            title=title,
            input_payload={
                **dict(input_payload or {}),
                "observed_step_key": step_key,
                "observed_step_title": title,
                "observed_step_summary": summary,
                "observed_step_goal": goal,
            },
            detail_json=detail_json,
            summary_message=summary,
        )
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_orchestration_detail(
                intent_type=task.intent_type or handler.spec.intent_type,
                entry_handler_key=task.entry_handler_key or handler.spec.entry_handler_key,
                handler_key=handler.spec.handler_key,
                semantic_step=title,
            ),
        )
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_semantic_step_detail(
                step_run_id=step.step_run_id,
                semantic_key=semantic_key,
                semantic_step=title,
                semantic_goal=goal,
                lifecycle="running",
            ),
        )
        return step

    def materialize_workflow_step(
        self,
        *,
        task: TaskRun,
        handler: TaskHandler,
        plan_step: TaskPlanStep,
        input_payload: dict,
        step_order: int,
    ) -> StepRun:
        """명시적 task_plan의 다음 의미 단계를 실행 StepRun으로 만든다.

        todo 항목은 StepRun 내부 체크리스트지만, task_plan의 step은 사용자가 보는 큰 작업 단위다.
        그래서 workflow 진행 시에만 새 StepRun anchor를 만들고, 일반 todo projection에는 이 경로를 쓰지 않는다.
        """

        step = StepRun(
            step_run_id=new_id("step"),
            task_run_id=task.task_run_id,
            step_order=step_order,
            step_type=handler.spec.step_type,
            handler_key=handler.spec.handler_key,
            status=StepStatus.PENDING,
            title=plan_step.title,
            input_payload={},
            detail_json=build_default_step_detail(),
            summary_message=plan_step.title,
        )
        return self.materialize_handoff_step(
            task=task,
            step=step,
            handler=handler,
            plan_step=plan_step,
            input_payload=input_payload,
        )

    def materialize_resume_step(self, *, task: TaskRun, step: StepRun, handler: TaskHandler) -> StepRun:
        """resume는 기존 StepRun을 재사용하되 semantic metadata가 비면 다시 채운다.

        StepRun은 approval과 waiting의 operational anchor(실행 이력을 묶는 기준점)이므로,
        재개 시에는 새 step을 만들지 않고 정확히 같은 step을 다시 RUNNING으로 올린다.
        """

        step.handler_key = step.handler_key or handler.spec.handler_key
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_orchestration_detail(
                intent_type=task.intent_type or handler.spec.intent_type,
                entry_handler_key=task.entry_handler_key or handler.spec.entry_handler_key,
                handler_key=step.handler_key,
                semantic_step=step.title or handler.spec.step_title,
            ),
        )
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_semantic_step_detail(
                step_run_id=step.step_run_id,
                semantic_key=self._handler_semantic_key(handler, fallback=step.step_type),
                semantic_step=step.title or handler.spec.step_title,
                semantic_goal=handler.spec.semantic_goal or step.title or handler.spec.step_title,
                lifecycle="resuming",
            ),
        )
        return step

    def materialize_handoff_step(
        self,
        *,
        task: TaskRun,
        step: StepRun,
        handler: TaskHandler,
        plan_step: TaskPlanStep,
        input_payload: dict,
    ) -> StepRun:
        """다음 workflow 단계로 넘어갈 때 projected step(계획에서 미리 만들어 둔 단계)을 실행 anchor(실행 이력을 묶는 기준점)로 승격한다."""

        step.step_type = handler.spec.step_type
        step.handler_key = handler.spec.handler_key
        step.title = plan_step.title
        next_input_payload = {
            **step.input_payload,
            **input_payload,
        }
        step.input_payload = self._with_plan_step_anchor(next_input_payload, plan_step)
        step.summary_message = plan_step.title
        step.detail_json = merge_step_detail(
            build_default_step_detail(),
            build_orchestration_detail(
                intent_type=task.intent_type or handler.spec.intent_type,
                entry_handler_key=task.entry_handler_key or handler.spec.entry_handler_key,
                handler_key=handler.spec.handler_key,
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
                    operation_templates=handler.spec.operation_templates,
                )
            ),
        )
        return step

    @staticmethod
    def _with_plan_step_anchor(input_payload: dict, plan_step: TaskPlanStep) -> dict:
        # explicit task_plan의 단계 anchor는 todo projection과 분리해 저장한다.
        payload = dict(input_payload or {})
        payload.pop("todo_key", None)
        payload.pop("todo_title", None)
        payload["plan_step_key"] = plan_step.key
        payload["plan_step_title"] = plan_step.title
        return payload

    @staticmethod
    def _handler_semantic_key(handler: TaskHandler, *, fallback: str | None = None) -> str:
        """handler 기본 semanticKey 생성 규칙.

        StepRun은 내부 operation이 아니라 의미 단위 anchor(사용자에게 보이는 단계 기준점)이므로,
        handler가 명시한 semantic_key를 우선 사용하고, fallback이 있으면 그 값을 쓰며,
        둘 다 없으면 step_type을 기준 semanticKey로 고정한다.
        """

        return handler.spec.semantic_key or fallback or handler.spec.step_type
