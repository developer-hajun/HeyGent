from __future__ import annotations

from app.contracts.task.step_status import StepStatus
from app.core.utils.ids import new_id
from app.tools.contracts import TaskHandler
from app.domain.orchestration.contracts import build_orchestration_detail
from app.domain.orchestration.runtime_planning.task_plan import build_task_plan
from app.domain.orchestration.runtime_planning.todo_state import TodoState, build_initial_todo_state, build_task_todo_payload
from app.domain.tasks.detail import build_default_step_detail, build_semantic_step_detail, merge_step_detail
from app.domain.tasks.models import StepRun, TaskRun


class Planner:
    """TaskRun / StepRun의 semantic(사용자에게 보이는 의미 단계) 골격을 만든다."""

    def materialize_task(
        self,
        *,
        owner_key: str,
        session_key: str | None,
        input_payload: dict,
        handler: TaskHandler,
        task_run_id: str | None = None,
    ) -> TaskRun:
        input_payload = self._normalized_input_payload(input_payload=input_payload, handler=handler)
        task_plan = build_task_plan(input_payload=input_payload, default_task_title=handler.spec.task_title)
        # agent.loop는 native tool call(모델이 구조화된 도구 호출을 직접 반환하는 방식)을 보고
        # 실행 중 todo projection(todo 상태를 화면/상태 detail로 투영한 값)을 갱신한다.
        # 그래서 명시적 task_plan이 없으면 고정 operation todo(미리 박아 둔 실행 단계 목록)를 만들지 않는다.
        initial_todo_state = (
            TodoState(items=(), current_key=None)
            if handler.spec.task_type == "agent.loop"
            else build_initial_todo_state(
                step_title=handler.spec.step_title,
                operation_templates=handler.spec.operation_templates,
            )
        )
        return TaskRun(
            task_run_id=task_run_id or new_id("task"),
            task_type=handler.spec.task_type,
            owner_key=owner_key,
            session_key=session_key,
            status="PENDING",
            title=task_plan.title if task_plan is not None and task_plan.title else handler.spec.task_title,
            input_payload=input_payload,
            todo_state=build_task_todo_payload(initial_todo_state),
        )

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

    def materialize_resume_step(self, *, task: TaskRun, step: StepRun, handler: TaskHandler) -> StepRun:
        """resume는 기존 StepRun을 재사용하되 semantic metadata가 비면 다시 채운다.

        StepRun은 approval과 waiting의 operational anchor(실행 이력을 묶는 기준점)이므로,
        재개 시에는 새 step을 만들지 않고 정확히 같은 step을 다시 RUNNING으로 올린다.
        """

        step.detail_json = merge_step_detail(
            step.detail_json,
            build_orchestration_detail(
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

    @staticmethod
    def _normalized_input_payload(*, input_payload: dict, handler: TaskHandler) -> dict:
        _ = handler
        return dict(input_payload or {})

    @staticmethod
    def _handler_semantic_key(handler: TaskHandler, *, fallback: str | None = None) -> str:
        """handler 기본 semanticKey 생성 규칙.

        StepRun은 내부 operation이 아니라 의미 단위 anchor(사용자에게 보이는 단계 기준점)이므로,
        handler가 명시한 semantic_key를 우선 사용하고, fallback이 있으면 그 값을 쓰며,
        둘 다 없으면 step_type을 기준 semanticKey로 고정한다.
        """

        return handler.spec.semantic_key or fallback or handler.spec.step_type
