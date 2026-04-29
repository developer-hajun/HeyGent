from __future__ import annotations

import json
import re

from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus
from app.core.time import utc_now
from app.domain.orchestration.agent.step_handler import StepHandler
from app.domain.orchestration.approval import ApprovalRuntime, ApprovalService
from app.domain.orchestration.delegation import ChildSessionLauncher, DelegateRuntime
from app.domain.orchestration.policies import (
    ensure_step_transition,
    ensure_task_transition,
    normalize_handler_outcome,
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
from app.domain.session.sessions.transcript_store import TranscriptStore
from app.domain.tasks.detail import (
    build_model_decision_detail,
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
        session_store: TranscriptStore | None = None,
    ) -> None:
        self.repository = repository
        self.broadcaster = broadcaster
        self.approval_service = approval_service
        self.child_session_launcher = child_session_launcher
        self.planner = planner
        self.tool_registry = tool_registry
        self.approval_runtime = ApprovalRuntime()
        self.delegate_runtime = DelegateRuntime(child_session_launcher, session_store=session_store)
        self.outcome_inspector = OutcomeInspector()
        self.step_handler = StepHandler()

    async def run(self, *, task: TaskRun, handler, step: StepRun | None = None) -> TaskRun:
        self.repository.create_task(task)
        await self._emit("task.created", task)
        if step is None:
            return await self._execute_initial(task=task, handler=handler, resume_payload=None)

        task.current_step_run_id = step.step_run_id
        self.repository.create_step(step)
        await self._emit("step.created", task, step)
        return await self._execute(task=task, step=step, handler=handler, resume_payload=None)

    async def _execute_initial(self, *, task: TaskRun, handler, resume_payload: dict | None) -> TaskRun:
        ensure_task_transition(task.status, TaskStatus.RUNNING)
        task.status = TaskStatus.RUNNING
        task.started_at = task.started_at or utc_now()
        task.wait_payload = {}
        task.current_step_run_id = None
        self.repository.update_task(task)
        await self._emit("task.started", task)

        try:
            outcome = normalize_handler_outcome(
                self.step_handler.execute(handler=handler, task=task, step=None, resume_payload=resume_payload)
            )
        except Exception as error:
            outcome = self._build_handler_failure_outcome(error)
            step = self.planner.materialize_step(
                task=task,
                handler=handler,
                input_payload=task.input_payload,
                step_order=1,
            )
            # 첫 provider 호출 전/중 실패는 아직 StepRun anchor가 없을 수 있으므로,
            # 기본 StepRun을 하나 만들어 실패 상태와 detail marker를 함께 남긴다.
            step.status = StepStatus.RUNNING
            step.started_at = step.started_at or task.started_at or utc_now()
            task.current_step_run_id = step.step_run_id
            self.repository.update_task(task)
            self.repository.create_step(step)
            await self._emit("step.created", task, step)
            await self._emit("step.started", task, step)
            return await self._apply_outcome(task=task, step=step, handler=handler, outcome=outcome)

        step = await self._materialize_initial_observed_steps(task=task, handler=handler, outcome=outcome)
        if step is None:
            step = self.planner.materialize_observed_step(
                task=task,
                handler=handler,
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
            return await self._apply_outcome(task=task, step=step, handler=handler, outcome=outcome)

        return await self._apply_outcome(task=task, step=step, handler=handler, outcome=outcome)

    async def _materialize_initial_observed_steps(self, *, task: TaskRun, handler, outcome: dict) -> StepRun | None:
        observed_steps = [item for item in outcome.get("observed_steps") or [] if isinstance(item, dict)]
        if not observed_steps:
            return None

        observed_step = self._current_observed_step(observed_steps)
        now = utc_now()
        step = self.planner.materialize_observed_semantic_step(
            task=task,
            handler=handler,
            input_payload=task.input_payload,
            step_order=1,
            observed_step=observed_step,
            outcome=outcome,
            include_outcome_detail=True,
        )
        task.current_step_run_id = step.step_run_id
        self.repository.update_task(task)
        self.repository.create_step(step)
        await self._emit("step.created", task, step)
        step.status = StepStatus.RUNNING
        step.started_at = step.started_at or task.started_at or now
        self.repository.update_step(step)
        await self._emit("step.started", task, step)
        return step

    @staticmethod
    def _current_observed_step(observed_steps: list[dict]) -> dict:
        # 한 번의 agent.loop outcome은 여러 표시용 StepRun을 선생성하지 않고,
        # 현재 진행 중이거나 다음으로 볼 의미 단계 하나만 StepRun anchor로 만든다.
        return next(
            (
                observed_step
                for observed_step in observed_steps
                if str(observed_step.get("status") or "").strip().lower() in {"in_progress", "pending"}
            ),
            observed_steps[-1],
        )

    async def resume(self, *, task: TaskRun, handler, approval_id: str, payload: dict) -> TaskRun:
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
        return await self._execute(task=task, step=step, handler=handler, resume_payload=payload)

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
        handler = None
        handler_key = step.handler_key or task.entry_handler_key
        if handler_key:
            handler = self.tool_registry.get(handler_key)

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
        self._record_pending_tool_cancellation(step=step, wait_payload=wait_payload, handler=handler)

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

        if handler is not None:
            await self._sync_todo_steps(task=task, handler=handler)

        await self._emit(
            "approval.canceled",
            task,
            step,
            payload={"approval_id": canceled_approval["approval_id"]},
        )
        await self._emit("step.canceled", task, step)
        await self._emit("task.canceled", task, step)
        return task

    def _record_pending_tool_cancellation(self, *, step: StepRun, wait_payload: dict, handler) -> None:
        tool_result = self._build_canceled_pending_tool_result(wait_payload)
        if tool_result is None:
            return

        output_payload = dict(step.output_payload or {})
        tool_results = list(output_payload.get("tool_results") or [])
        if not any(str(item.get("tool_call_id") or "") == tool_result["tool_call_id"] for item in tool_results if isinstance(item, dict)):
            tool_results.append(tool_result)
        output_payload["tool_results"] = tool_results
        step.output_payload = output_payload

        session_store = self._session_store_from_handler(handler)
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
    def _session_store_from_handler(handler) -> TranscriptStore | None:
        loop_handler = getattr(handler, "loop_handler", None)
        return getattr(loop_handler, "session_store", None)

    async def _execute(self, *, task: TaskRun, step: StepRun, handler, resume_payload: dict | None) -> TaskRun:
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
                semantic_key=semantic_key_of(step.detail_json) or handler.spec.semantic_key or step.step_type,
                semantic_step=(step.detail_json.get("semanticDetail") or {}).get("semanticStep") or step.title or handler.spec.step_title,
                semantic_goal=(step.detail_json.get("semanticDetail") or {}).get("goal") or handler.spec.semantic_goal or step.title or handler.spec.step_title,
                lifecycle="running",
                status=infer_semantic_status(lifecycle="running", operation_detail=step.detail_json.get("operationDetail")),
            ),
        )
        self.repository.update_task(task)
        self.repository.update_step(step)
        await self._emit("task.started", task)
        await self._emit("step.started", task, step)

        try:
            outcome = normalize_handler_outcome(
                self.step_handler.execute(handler=handler, task=task, step=step, resume_payload=resume_payload)
            )
        except Exception as error:
            # 이미 materialized 된 StepRun이 있으면 같은 anchor를 FAILED로 닫아
            # approval/resume과 이벤트 기준점이 바뀌지 않게 한다.
            outcome = self._build_handler_failure_outcome(error)
        return await self._apply_outcome(task=task, step=step, handler=handler, outcome=outcome)

    def _build_handler_failure_outcome(self, error: Exception) -> dict:
        error_message = self._safe_error_message(error)
        summary_message = "작업 처리 중 오류가 발생했습니다."
        retryable = self._handler_error_retryable(error)
        return {
            "task_status": TaskStatus.FAILED,
            "step_status": StepStatus.FAILED,
            "result_payload": {},
            "output_payload": {
                "error": {
                    "type": type(error).__name__,
                    "message": error_message,
                    "recovery": {
                        "diagnose": True,
                        "retryable": retryable,
                        "retry_attempted": False,
                        "retry_policy": "manual_or_next_loop",
                    },
                }
            },
            "wait_payload": {},
            "detail_json": build_model_decision_detail(
                action="diagnose_then_fail",
                action_summary="오류 원인을 기록하고 재시도 가능성을 남긴 뒤 종료했습니다.",
            ),
            "todo_state": {},
            "summary_message": summary_message,
            "error_message": error_message,
            "operations": [
                {
                    "key": "handler.diagnose",
                    "title": "오류 원인 기록",
                    "kind": "execute",
                    "status": "completed",
                    "summary": error_message,
                },
                {
                    "key": "handler.retry.unavailable",
                    "title": "재시도 후보 기록",
                    "kind": "execute",
                    "status": "waiting" if retryable else "completed",
                    "summary": "자동 재시도 없이 다음 판단 또는 수동 재개 대상으로 남겼습니다.",
                },
                {
                    "key": "handler.failure",
                    "title": "실행 실패",
                    "kind": "execute",
                    "status": "failed",
                    "summary": error_message,
                }
            ],
        }

    @staticmethod
    def _handler_error_retryable(error: Exception) -> bool:
        retryable_names = {
            "TimeoutError",
            "ConnectionError",
            "RuntimeError",
        }
        return type(error).__name__ in retryable_names

    @staticmethod
    def _safe_error_message(error: Exception) -> str:
        error_type = type(error).__name__
        raw_message = str(error).strip() or "상세 메시지가 없습니다."
        first_line = raw_message.splitlines()[0] if raw_message.splitlines() else raw_message
        compact_message = " ".join(first_line.split())
        redacted_message = TaskEngine._redact_sensitive_error_text(compact_message)
        if len(redacted_message) > 180:
            redacted_message = redacted_message[:177].rstrip() + "..."
        return f"{error_type}: {redacted_message}"

    @staticmethod
    def _redact_sensitive_error_text(message: str) -> str:
        redacted = re.sub(r"sk-[A-Za-z0-9_-]{10,}", "[redacted]", message)
        redacted = re.sub(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [redacted]", redacted)
        redacted = re.sub(
            r"(?i)\b(api[_-]?key|token|secret|password)\s*[:=]\s*[^,\s]+",
            r"\1=[redacted]",
            redacted,
        )
        return redacted

    async def _apply_outcome(self, *, task: TaskRun, step: StepRun, handler, outcome: dict) -> TaskRun:
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
        observed_semantic_key = self._observed_semantic_key(step)
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_semantic_step_detail(
                step_run_id=step.step_run_id,
                semantic_key=semantic_key_of(step.detail_json) or observed_semantic_key or step.step_type,
                semantic_step=(step.detail_json.get("semanticDetail") or {}).get("semanticStep")
                or step.input_payload.get("observed_step_title")
                or step.title
                or step.step_type,
                semantic_goal=(step.detail_json.get("semanticDetail") or {}).get("goal")
                or step.input_payload.get("observed_step_goal")
                or step.title
                or step.step_type,
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
        await self._sync_todo_steps(task=task, handler=handler)

        next_task = await self._maybe_continue_workflow(task=task, step=step)
        if next_task is not None:
            return next_task

        if task_is_terminal(task_status):
            # explicit task_plan은 completed outcome 이후에도 다음 의미 단계가 남을 수 있다.
            # continuation 판단이 끝난 뒤에만 일반 agent.loop의 미완료 todo를 닫는다.
            task.todo_state = build_task_todo_payload(cancel_incomplete_task_todo_items(task.todo_state))
            self.repository.update_task(task)
            await self._sync_todo_steps(task=task, handler=handler)

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

    @staticmethod
    def _observed_semantic_key(step: StepRun) -> str | None:
        observed_step_key = str(step.input_payload.get("observed_step_key") or "").strip()
        if not observed_step_key:
            return None
        return f"observed.{observed_step_key}"

    async def _maybe_continue_workflow(self, *, task: TaskRun, step: StepRun) -> TaskRun | None:
        if task.status != TaskStatus.COMPLETED:
            return None

        plan = build_task_plan(input_payload=task.input_payload, default_task_title=task.title)
        if plan is None:
            return None

        current_plan_step_key = str(step.input_payload.get("plan_step_key") or "").strip() or None
        if current_plan_step_key is not None:
            completed_state = update_task_todo_item_status(
                task.todo_state,
                key=current_plan_step_key,
                status="completed",
                advance_current=True,
            )
            task.todo_state = build_task_todo_payload(completed_state)
            self.repository.update_task(task)
            await self._sync_todo_steps(task=task, handler=self.tool_registry.get(step.handler_key or task.entry_handler_key))

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
        next_handler = self._resolve_workflow_handler(task=task, step_key=plan_step.key)
        next_payload = self._build_handoff_input(task=task, step=step, next_step=plan_step)
        task.status = TaskStatus.PENDING
        task.ended_at = None
        task.input_payload = next_payload
        self.repository.update_task(task)
        await self._sync_todo_steps(task=task, handler=next_handler)

        existing_steps = self.repository.list_steps(task.task_run_id)
        projected = next(
            (
                candidate
                for candidate in existing_steps
                if str(candidate.input_payload.get("plan_step_key") or "").strip() == plan_step.key
            ),
            None,
        )
        step_order = max((candidate.step_order for candidate in existing_steps), default=0) + 1
        if projected is None:
            projected = self.planner.materialize_workflow_step(
                task=task,
                handler=next_handler,
                plan_step=plan_step,
                input_payload=next_payload,
                step_order=step_order,
            )
            self.repository.create_step(projected)
        else:
            projected = self.planner.materialize_handoff_step(
                task=task,
                step=projected,
                handler=next_handler,
                plan_step=plan_step,
                input_payload=next_payload,
            )
            self.repository.update_step(projected)

        return await self._execute(task=task, step=projected, handler=next_handler, resume_payload=None)

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
        saved_event = self.repository.append_event(event)
        await self.broadcaster.publish(saved_event)

    async def _sync_todo_steps(self, *, task: TaskRun, handler) -> None:
        todo_state = parse_task_todo_payload(task.todo_state)
        if not todo_state.items:
            return
        if not task.current_step_run_id:
            return

        current_step = self.repository.get_step(task.current_step_run_id)
        if current_step is None:
            return

        # todo는 사용자에게 보이는 새 의미 단계가 아니라 현재 StepRun 내부 체크리스트다.
        # 따라서 task.todo_state와 현재 StepRun.detail_json.planningDetail만 같은 상태로 맞추고,
        # todo 항목마다 StepRun을 생성하거나 재사용하는 projection 경로는 열지 않는다.
        current_step.detail_json = merge_step_detail(
            current_step.detail_json,
            build_planning_detail(
                todo_items=[
                    {
                        "key": item.key,
                        "title": item.title,
                        "kind": item.kind,
                        "status": item.status,
                    }
                    for item in todo_state.items
                ],
                current_key=todo_state.current_key,
            ),
        )
        self.repository.update_step(current_step)

    def _resolve_workflow_handler(self, *, task: TaskRun, step_key: str):
        plan = build_task_plan(input_payload=task.input_payload, default_task_title=task.title)
        plan_step = find_task_plan_step(plan, step_key=step_key)
        if plan_step is None:
            return self.tool_registry.resolve(intent_type=task.intent_type, entry_handler_key=task.entry_handler_key)
        return self.tool_registry.resolve(
            intent_type=plan_step.intent_type or task.intent_type,
            entry_handler_key=plan_step.entry_handler_key or task.entry_handler_key,
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
