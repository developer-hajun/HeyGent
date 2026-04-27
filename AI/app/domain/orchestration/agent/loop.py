from __future__ import annotations

import json

from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus
from app.core.time import utc_now
from app.domain.orchestration.agent.step_executor import StepExecutor
from app.domain.orchestration.approval import ApprovalRuntime, ApprovalService
from app.domain.orchestration.delegation import ChildSessionLauncher, DelegateRuntime
from app.domain.orchestration.policies import (
    decide_todo_projection_boundary,
    ensure_step_transition,
    ensure_task_transition,
    normalize_executor_outcome,
    semantic_lifecycle_for_status,
    task_is_terminal,
)
from app.domain.orchestration.runtime_planning import Planner, build_task_plan, find_task_plan_step
from app.domain.orchestration.runtime_planning.todo_state import (
    build_task_todo_payload,
    cancel_incomplete_task_todo_items,
    parse_task_todo_payload,
    update_task_todo_item_status,
)
from app.domain.orchestration.result_inspector import OutcomeInspector
from app.domain.tasks.detail import (
    build_planning_detail,
    build_semantic_step_detail,
    infer_semantic_status,
    merge_step_detail,
    semantic_key_of,
)
from app.domain.tasks.events import build_task_event
from app.domain.tasks.repository import TaskRepository
from app.domain.tasks.models import StepRun, TaskRun


class TaskEngine:
    """Coordinate task execution, approval waiting, and exact-step resume."""

    def __init__(
        self,
        repository: TaskRepository,
        broadcaster,
        approval_service: ApprovalService,
        child_session_launcher: ChildSessionLauncher,
        planner: Planner,
        tool_registry,
    ) -> None:
        self.repository = repository
        self.broadcaster = broadcaster
        self.approval_service = approval_service
        self.child_session_launcher = child_session_launcher
        self.planner = planner
        self.tool_registry = tool_registry
        self.approval_runtime = ApprovalRuntime()
        self.delegate_runtime = DelegateRuntime(child_session_launcher)
        self.outcome_inspector = OutcomeInspector()
        self.step_executor = StepExecutor()

    async def run(self, *, task: TaskRun, executor, step: StepRun | None = None) -> TaskRun:
        self.repository.create_task(task)
        await self._emit("task.created", task)
        if step is None:
            return await self._execute_initial(task=task, executor=executor, resume_payload=None)

        task.current_step_run_id = step.step_run_id
        self.repository.create_step(step)
        await self._emit("step.created", task, step)
        return await self._execute(task=task, step=step, executor=executor, resume_payload=None)

    async def _execute_initial(self, *, task: TaskRun, executor, resume_payload: dict | None) -> TaskRun:
        ensure_task_transition(task.status, TaskStatus.RUNNING)
        task.status = TaskStatus.RUNNING
        task.started_at = task.started_at or utc_now()
        task.wait_payload = {}
        task.current_step_run_id = None
        self.repository.update_task(task)
        await self._emit("task.started", task)

        outcome = normalize_executor_outcome(
            self.step_executor.execute(handler=executor, task=task, step=None, resume_payload=resume_payload)
        )
        step = self.planner.materialize_observed_step(
            task=task,
            executor=executor,
            input_payload=task.input_payload,
            step_order=1,
            outcome=outcome,
        )
        step.status = StepStatus.RUNNING
        step.started_at = step.started_at or task.started_at or utc_now()
        task.current_step_run_id = step.step_run_id
        self.repository.update_task(task)
        self.repository.create_step(step)
        await self._emit("step.created", task, step)
        await self._emit("step.started", task, step)
        return await self._apply_outcome(task=task, step=step, executor=executor, outcome=outcome)

    async def resume(self, *, task: TaskRun, executor, approval_id: str, payload: dict) -> TaskRun:
        approval = self.approval_service.resolve(approval_id, payload)
        if approval is None:
            raise KeyError(approval_id)

        step = self.repository.get_step(approval["step_run_id"])
        if step is None:
            raise KeyError(approval["step_run_id"])
        task.current_step_run_id = step.step_run_id
        self.approval_runtime.mark_resolved_step(step=step, approval_id=approval_id, response_payload=payload)
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_semantic_step_detail(
                step_run_id=step.step_run_id,
                semantic_key=semantic_key_of(step.detail_json) or step.step_type,
                semantic_step=(step.detail_json.get("semanticDetail") or {}).get("semanticStep") or step.title or step.step_type,
                semantic_goal=(step.detail_json.get("semanticDetail") or {}).get("goal") or step.title or step.step_type,
                lifecycle="resuming",
                status=infer_semantic_status(lifecycle="resuming", operation_detail=step.detail_json.get("operationDetail")),
            ),
        )
        self.repository.update_step(step)
        await self._emit("approval.resolved", task, step, payload={"approval_id": approval_id, **payload})
        return await self._execute(task=task, step=step, executor=executor, resume_payload=payload)

    async def cancel_waiting(self, *, task: TaskRun) -> TaskRun:
        if task.status != TaskStatus.WAITING:
            raise ValueError("task is not waiting")
        if not task.current_step_run_id:
            raise ValueError("task waiting step is missing")

        step = self.repository.get_step(task.current_step_run_id)
        if step is None:
            raise KeyError(task.current_step_run_id)
        if step.status != StepStatus.WAITING:
            raise ValueError("current step is not waiting")

        wait_payload = dict(step.wait_payload or {})
        executor = None
        executor_key = step.executor_key or task.entry_executor_key
        if executor_key:
            executor = self.tool_registry.get(executor_key)

        approval = self.repository.get_open_approval(task.task_run_id)
        if approval is None:
            raise ValueError("no open approval")
        canceled_approval = self.approval_service.cancel(approval["approval_id"])
        if canceled_approval is None:
            raise ValueError("no open approval")

        canceled_at = utc_now()
        self.approval_runtime.mark_canceled_step(
            step=step,
            approval_id=canceled_approval["approval_id"],
            request_payload=canceled_approval.get("request_payload"),
        )
        self._record_pending_tool_cancellation(step=step, wait_payload=wait_payload, executor=executor)

        task.status = TaskStatus.CANCELED
        task.wait_payload = {}
        task.progress_summary = "작업이 취소되었습니다."
        task.current_step_run_id = step.step_run_id
        task.todo_state = build_task_todo_payload(cancel_incomplete_task_todo_items(task.todo_state))
        task.revision += 1
        task.ended_at = canceled_at

        step.status = StepStatus.CANCELED
        step.wait_payload = {}
        step.summary_message = "사용자 요청으로 취소됨"
        step.ended_at = canceled_at
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_semantic_step_detail(
                step_run_id=step.step_run_id,
                semantic_key=semantic_key_of(step.detail_json) or step.step_type,
                semantic_step=(step.detail_json.get("semanticDetail") or {}).get("semanticStep") or step.title or step.step_type,
                semantic_goal=(step.detail_json.get("semanticDetail") or {}).get("goal") or step.title or step.step_type,
                lifecycle="canceled",
                status=infer_semantic_status(lifecycle="canceled", operation_detail=step.detail_json.get("operationDetail")),
            ),
        )

        self.repository.update_task(task)
        self.repository.update_step(step)

        if executor is not None:
            await self._sync_todo_steps(task=task, executor=executor)

        await self._emit(
            "approval.canceled",
            task,
            step,
            payload={"approval_id": canceled_approval["approval_id"]},
        )
        await self._emit("step.canceled", task, step)
        await self._emit("task.canceled", task, step)
        return task

    def _record_pending_tool_cancellation(self, *, step: StepRun, wait_payload: dict, executor) -> None:
        tool_result = self._build_canceled_pending_tool_result(wait_payload)
        if tool_result is None:
            return

        output_payload = dict(step.output_payload or {})
        tool_results = list(output_payload.get("tool_results") or [])
        if not any(str(item.get("tool_call_id") or "") == tool_result["tool_call_id"] for item in tool_results if isinstance(item, dict)):
            tool_results.append(tool_result)
        output_payload["tool_results"] = tool_results
        step.output_payload = output_payload

        session_store = self._session_store_from_executor(executor)
        transcript_session_id = str(wait_payload.get("transcript_session_id") or "").strip()
        if session_store is None or not transcript_session_id or session_store.get_session(transcript_session_id) is None:
            return

        result = tool_result["result"]
        content = result.get("content") if isinstance(result, dict) else None
        session_store.append_message(
            session_id=transcript_session_id,
            role="tool",
            content=str(content or json.dumps(result, ensure_ascii=False)),
            tool_name=tool_result["name"],
            tool_call_id=tool_result["tool_call_id"],
        )

    @staticmethod
    def _build_canceled_pending_tool_result(wait_payload: dict) -> dict | None:
        call_id = str(wait_payload.get("pending_tool_call_id") or "").strip()
        tool_name = str(wait_payload.get("pending_tool_name") or "").strip()
        args = wait_payload.get("pending_tool_arguments")
        if not call_id or not tool_name or not isinstance(args, dict):
            return None

        message = "task canceled before pending tool execution"
        return {
            "tool_call_id": call_id,
            "name": tool_name,
            "args": args,
            "result": {
                "ok": False,
                "content": f"Tool call canceled: {message}",
                "error": {
                    "code": "tool_canceled",
                    "message": message,
                    "tool_name": tool_name,
                },
                "canceled": True,
            },
        }

    @staticmethod
    def _session_store_from_executor(executor):
        loop_executor = getattr(executor, "loop_executor", None)
        return getattr(loop_executor, "session_store", None)

    async def _execute(self, *, task: TaskRun, step: StepRun, executor, resume_payload: dict | None) -> TaskRun:
        ensure_task_transition(task.status, TaskStatus.RUNNING)
        ensure_step_transition(step.status, StepStatus.RUNNING)

        task.status = TaskStatus.RUNNING
        task.started_at = task.started_at or utc_now()
        task.wait_payload = {}
        task.current_step_run_id = step.step_run_id
        step.status = StepStatus.RUNNING
        step.started_at = step.started_at or utc_now()
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_semantic_step_detail(
                step_run_id=step.step_run_id,
                semantic_key=semantic_key_of(step.detail_json) or executor.spec.semantic_key or step.step_type,
                semantic_step=(step.detail_json.get("semanticDetail") or {}).get("semanticStep") or step.title or executor.spec.step_title,
                semantic_goal=(step.detail_json.get("semanticDetail") or {}).get("goal") or executor.spec.semantic_goal or step.title or executor.spec.step_title,
                lifecycle="running",
                status=infer_semantic_status(lifecycle="running", operation_detail=step.detail_json.get("operationDetail")),
            ),
        )
        self.repository.update_task(task)
        self.repository.update_step(step)
        await self._emit("task.started", task)
        await self._emit("step.started", task, step)

        outcome = normalize_executor_outcome(
            self.step_executor.execute(handler=executor, task=task, step=step, resume_payload=resume_payload)
        )
        return await self._apply_outcome(task=task, step=step, executor=executor, outcome=outcome)

    async def _apply_outcome(self, *, task: TaskRun, step: StepRun, executor, outcome: dict) -> TaskRun:
        outcome = await self.delegate_runtime.apply(task=task, step=step, outcome=outcome, repository=self.repository)
        # operation-only outcome 은 새 StepRun 생성 사유가 아니다. semanticKey 가 유지되는 한
        # result_inspector 가 기존 step.detail_json.operationDetail 에 operation 을 누적한다.
        outcome = self.outcome_inspector.inspect(step=step, outcome=outcome)
        task_status = outcome["task_status"]
        step_status = outcome["step_status"]
        ensure_task_transition(task.status, task_status)
        ensure_step_transition(step.status, step_status)

        task.status = task_status
        step.status = step_status
        task.current_step_run_id = step.step_run_id
        task.result_payload = outcome.get("result_payload", task.result_payload)
        task.todo_state = dict(outcome.get("todo_state") or task.todo_state)
        task.wait_payload = outcome.get("wait_payload", {})
        task.error_message = outcome.get("error_message")
        task.progress_summary = outcome.get("summary_message")
        task.revision += 1
        step.output_payload = outcome.get("output_payload", step.output_payload)
        step.wait_payload = outcome.get("wait_payload", {})
        step.error_message = outcome.get("error_message")
        step.detail_json = merge_step_detail(step.detail_json, outcome.get("detail_json"))
        semantic_lifecycle = semantic_lifecycle_for_status(task_status)
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_semantic_step_detail(
                step_run_id=step.step_run_id,
                semantic_key=semantic_key_of(step.detail_json) or step.step_type,
                semantic_step=(step.detail_json.get("semanticDetail") or {}).get("semanticStep") or step.title or step.step_type,
                semantic_goal=(step.detail_json.get("semanticDetail") or {}).get("goal") or step.title or step.step_type,
                lifecycle=semantic_lifecycle,
                status=infer_semantic_status(lifecycle=semantic_lifecycle, operation_detail=step.detail_json.get("operationDetail")),
            ),
        )
        step.summary_message = outcome.get("summary_message")
        if task_is_terminal(task_status):
            task.ended_at = utc_now()
            step.ended_at = utc_now()
        self.repository.update_task(task)
        self.repository.update_step(step)
        await self._sync_todo_steps(task=task, executor=executor)

        next_task = await self._maybe_continue_workflow(task=task, step=step)
        if next_task is not None:
            return next_task

        if task_status == TaskStatus.WAITING:
            approval = self.approval_service.request(
                task_run_id=task.task_run_id,
                step_run_id=step.step_run_id,
                payload=outcome.get("approval_payload", {}),
            )
            self.approval_runtime.attach_waiting_approval(task=task, step=step, approval=approval)
            self.repository.update_task(task)
            self.repository.update_step(step)
            await self._emit("approval.requested", task, step, payload=approval)
            await self._emit("task.waiting", task, step)
            await self._emit("step.waiting", task, step)
            return task

        if task_status == TaskStatus.COMPLETED:
            await self._emit("step.completed", task, step)
            await self._emit("task.completed", task, step, payload=task.result_payload)
            return task

        if task_status == TaskStatus.FAILED:
            await self._emit("step.failed", task, step, payload={"error_message": step.error_message})
            await self._emit("task.failed", task, step, payload={"error_message": task.error_message})
            return task

        if task_status == TaskStatus.CANCELED:
            await self._emit("step.canceled", task, step)
            await self._emit("task.canceled", task, step)
            return task

        await self._emit("task.updated", task, step)
        return task

    async def _maybe_continue_workflow(self, *, task: TaskRun, step: StepRun) -> TaskRun | None:
        if task.status != TaskStatus.COMPLETED:
            return None

        plan = build_task_plan(input_payload=task.input_payload, default_task_title=task.title)
        if plan is None:
            return None

        current_todo_key = str(step.input_payload.get("todo_key") or "").strip() or None
        if current_todo_key is not None:
            completed_state = update_task_todo_item_status(
                task.todo_state,
                key=current_todo_key,
                status="completed",
                advance_current=True,
            )
            task.todo_state = build_task_todo_payload(completed_state)
            self.repository.update_task(task)
            await self._sync_todo_steps(task=task, executor=self.tool_registry.get(step.executor_key or task.entry_executor_key))

        todo_state = parse_task_todo_payload(task.todo_state)
        next_item = next((item for item in todo_state.items if item.key == todo_state.current_key), None)
        if next_item is None:
            return None

        plan_step = find_task_plan_step(plan, step_key=next_item.key)
        if plan_step is None:
            return None

        in_progress_state = update_task_todo_item_status(
            task.todo_state,
            key=plan_step.key,
            status="in_progress",
            advance_current=False,
        )
        task.todo_state = build_task_todo_payload(in_progress_state)
        next_executor = self._resolve_workflow_executor(task=task, step_key=plan_step.key)
        next_payload = self._build_handoff_input(task=task, step=step, next_step=plan_step)
        task.status = TaskStatus.PENDING
        task.ended_at = None
        task.input_payload = next_payload
        self.repository.update_task(task)
        await self._sync_todo_steps(task=task, executor=next_executor)

        existing_steps = self.repository.list_steps(task.task_run_id)
        projected = next(
            (
                candidate
                for candidate in existing_steps
                if str(candidate.input_payload.get("todo_key") or "").strip() == plan_step.key
            ),
            None,
        )
        step_order = max((candidate.step_order for candidate in existing_steps), default=0) + 1
        if projected is None:
            projected = self.planner.materialize_todo_step(
                task=task,
                executor=next_executor,
                todo_item=next_item,
                step_order=step_order,
            )
            projected = self.planner.materialize_handoff_step(
                task=task,
                step=projected,
                executor=next_executor,
                plan_step=plan_step,
                input_payload=next_payload,
            )
            self.repository.create_step(projected)
        else:
            projected = self.planner.materialize_handoff_step(
                task=task,
                step=projected,
                executor=next_executor,
                plan_step=plan_step,
                input_payload=next_payload,
            )
            self.repository.update_step(projected)

        return await self._execute(task=task, step=projected, executor=next_executor, resume_payload=None)

    async def _emit(self, event_type: str, task: TaskRun, step: StepRun | None = None, payload: dict | None = None) -> None:
        event = build_task_event(
            event_type=event_type,
            task_run_id=task.task_run_id,
            step_run_id=step.step_run_id if step else None,
            producer="task_engine",
            status=task.status,
            summary_message=task.progress_summary,
            payload=payload or {},
        )
        self.repository.append_event(event)
        await self.broadcaster.publish(event)

    async def _sync_todo_steps(self, *, task: TaskRun, executor) -> None:
        todo_state = parse_task_todo_payload(task.todo_state)
        if not todo_state.items:
            return

        existing_steps = self.repository.list_steps(task.task_run_id)
        projected_steps = {
            str(step.input_payload.get("todo_key") or "").strip(): step
            for step in existing_steps
            if str(step.input_payload.get("todo_key") or "").strip()
        }
        next_order = max((step.step_order for step in existing_steps), default=0) + 1

        for item in todo_state.items:
            target_status = self._todo_status_to_step_status(item.status)
            projected = projected_steps.get(item.key)
            boundary = decide_todo_projection_boundary(
                existing_step_run_id=projected.step_run_id if projected is not None else None,
            )
            if boundary.action == "create_new_step":
                projected = self.planner.materialize_todo_step(
                    task=task,
                    executor=executor,
                    todo_item=item,
                    step_order=next_order,
                )
                next_order += 1
                projected.status = target_status
                now = utc_now()
                if target_status != StepStatus.PENDING:
                    projected.started_at = now
                if target_status in {StepStatus.COMPLETED, StepStatus.CANCELED, StepStatus.FAILED}:
                    projected.ended_at = now
                projected.detail_json = merge_step_detail(
                    projected.detail_json,
                    build_semantic_step_detail(
                        step_run_id=projected.step_run_id,
                        semantic_key=f"todo.{item.key}",
                        semantic_step=item.title,
                        semantic_goal=item.title,
                        lifecycle=self._todo_lifecycle(item.status),
                        status=infer_semantic_status(lifecycle=self._todo_lifecycle(item.status), operation_detail=projected.detail_json.get("operationDetail")),
                    ),
                )
                self.repository.create_step(projected)
                continue

            if projected is None:
                continue
            projected.title = item.title
            projected.input_payload = {
                **projected.input_payload,
                "todo_key": item.key,
                "todo_title": item.title,
                "todo_status": item.status,
            }
            projected.summary_message = item.title
            projected.status = target_status
            projected.detail_json = merge_step_detail(
                projected.detail_json,
                build_semantic_step_detail(
                    step_run_id=projected.step_run_id,
                    semantic_key=f"todo.{item.key}",
                    semantic_step=item.title,
                    semantic_goal=item.title,
                    lifecycle=self._todo_lifecycle(item.status),
                    status=infer_semantic_status(lifecycle=self._todo_lifecycle(item.status), operation_detail=projected.detail_json.get("operationDetail")),
                ),
            )
            projected.detail_json = merge_step_detail(
                projected.detail_json,
                build_planning_detail(
                    todo_items=[
                        {
                            "key": item.key,
                            "title": item.title,
                            "kind": item.kind,
                            "status": item.status,
                        }
                    ],
                    current_key=item.key if item.status in {"pending", "in_progress"} else None,
                ),
            )
            now = utc_now()
            if target_status != StepStatus.PENDING and projected.started_at is None:
                projected.started_at = now
            if target_status in {StepStatus.COMPLETED, StepStatus.CANCELED, StepStatus.FAILED}:
                projected.ended_at = projected.ended_at or now
            else:
                projected.ended_at = None
            self.repository.update_step(projected)

    @staticmethod
    def _todo_status_to_step_status(todo_status: str) -> str:
        normalized = str(todo_status or "pending").strip().lower()
        if normalized == "in_progress":
            return StepStatus.RUNNING
        if normalized == "completed":
            return StepStatus.COMPLETED
        if normalized == "cancelled":
            return StepStatus.CANCELED
        return StepStatus.PENDING

    @staticmethod
    def _todo_lifecycle(todo_status: str) -> str:
        normalized = str(todo_status or "pending").strip().lower()
        if normalized == "in_progress":
            return "running"
        if normalized == "completed":
            return "completed"
        if normalized == "cancelled":
            return "canceled"
        return "pending"

    def _resolve_workflow_executor(self, *, task: TaskRun, step_key: str):
        plan = build_task_plan(input_payload=task.input_payload, default_task_title=task.title)
        plan_step = find_task_plan_step(plan, step_key=step_key)
        if plan_step is None:
            return self.tool_registry.resolve(intent_type=task.intent_type, entry_executor_key=task.entry_executor_key)
        return self.tool_registry.resolve(
            intent_type=plan_step.intent_type or task.intent_type,
            entry_executor_key=plan_step.entry_executor_key or task.entry_executor_key,
        )

    @staticmethod
    def _build_handoff_input(*, task: TaskRun, step: StepRun, next_step) -> dict:
        previous_payload = dict(task.input_payload or {})
        previous_prompt = str(previous_payload.get("prompt") or "").strip()
        previous_text = str((task.result_payload or {}).get("text") or (task.result_payload or {}).get("summary") or "").strip()
        model_decision_detail = (step.detail_json or {}).get("modelDecisionDetail") or {}
        previous_handoff_summary = str(
            model_decision_detail.get("handoffSummary") or (task.result_payload or {}).get("handoff_summary") or ""
        ).strip()
        preferred_previous_text = previous_handoff_summary or previous_text
        merged = {
            **previous_payload,
            **dict(next_step.input_payload or {}),
            "workflow_handoff": {
                "fromStepRunId": step.step_run_id,
                "fromStepTitle": step.title,
                "toStepKey": next_step.key,
                "toStepTitle": next_step.title,
                "previousPrompt": previous_prompt,
                "previousHandoffSummary": previous_handoff_summary or None,
                "previousResultText": previous_text or None,
                "previousResult": task.result_payload,
            },
        }
        merged["prompt"] = "\n\n".join(
            part
            for part in [
                f"현재 단계: {next_step.title}",
                f"목표: {next_step.goal}",
                f"이전 단계: {step.title}",
                f"이전 단계 인계 요약: {previous_handoff_summary}" if previous_handoff_summary else None,
                f"이전 결과 요약: {previous_text}" if previous_text and previous_text != previous_handoff_summary else None,
                f"원래 사용자 요청: {previous_prompt}" if previous_prompt else None,
            ]
            if part
        )
        return merged
