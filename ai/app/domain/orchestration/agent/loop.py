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
from app.domain.orchestration.runtime_planning import (
    Planner,
)
from app.domain.orchestration.runtime_planning.todo_state import (
    build_task_todo_payload,
    cancel_incomplete_task_todo_items,
    parse_task_todo_payload,
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
                await self.step_handler.execute(
                    handler=handler,
                    task=task,
                    step=None,
                    resume_payload=resume_payload,
                    progress_sink=self._build_progress_sink(task=task, step=None),
                )
            )
        except Exception as error:
            outcome = self._build_handler_failure_outcome(error)
            step = self.planner.materialize_step(
                task=task,
                handler=handler,
                input_payload=task.input_payload,
                step_order=1,
            )
            # provider 호출 실패처럼 모델 관찰값이 없는 경우에만 사후 실패 anchor를 만든다.
            step.status = StepStatus.RUNNING
            step.started_at = step.started_at or task.started_at or utc_now()
            task.current_step_run_id = step.step_run_id
            self.repository.update_task(task)
            self.repository.create_step(step)
            await self._emit("step.created", task, step)
            await self._emit("step.started", task, step)
            return await self._apply_outcome(task=task, step=step, handler=handler, outcome=outcome)

        live_step = self.repository.get_step(task.current_step_run_id) if task.current_step_run_id else None
        if live_step is not None:
            return await self._apply_outcome(task=task, step=live_step, handler=handler, outcome=outcome)

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

    async def _materialize_initial_observed_steps(
        self,
        *,
        task: TaskRun,
        handler,
        outcome: dict,
    ) -> StepRun | None:
        observed_steps = [item for item in outcome.get("observed_steps") or [] if isinstance(item, dict)]
        if not observed_steps:
            return None

        observed_step = self._current_observed_step(observed_steps)
        now = utc_now()
        active_step: StepRun | None = None
        for index, candidate in enumerate(self._observed_steps_to_materialize(observed_steps, observed_step), start=1):
            materialized_step = self.planner.materialize_observed_semantic_step(
                task=task,
                handler=handler,
                input_payload=task.input_payload,
                step_order=index,
                observed_step=candidate,
                outcome=outcome,
                include_outcome_detail=candidate is observed_step,
            )
            step = materialized_step
            self.repository.create_step(step)
            await self._emit("step.created", task, step)

            step.status = StepStatus.RUNNING
            step.started_at = step.started_at or task.started_at or now
            self.repository.update_step(step)
            await self._emit("step.started", task, step)

            if candidate is observed_step:
                active_step = step
                continue

            # 모델이 이미 완료했다고 선언한 선행 의미 단계는 별도 StepRun으로 닫아
            # 프론트가 한 요청 안의 사용자 가시 단계를 여러 줄로 복원할 수 있게 한다.
            if str(candidate.get("status") or "").strip().lower() == "completed":
                step.status = StepStatus.COMPLETED
                step.ended_at = step.ended_at or now
                step.detail_json = merge_step_detail(
                    step.detail_json,
                    build_semantic_step_detail(
                        step_run_id=step.step_run_id,
                        semantic_key=semantic_key_of(step.detail_json) or self._observed_semantic_key(step) or step.step_type,
                        semantic_step=step.input_payload.get("observed_step_title") or step.title or step.step_type,
                        semantic_goal=step.input_payload.get("observed_step_goal") or step.title or step.step_type,
                        lifecycle="completed",
                        status=infer_semantic_status(
                            lifecycle="completed",
                            operation_detail=step.detail_json.get("operationDetail"),
                        ),
                    ),
                )
                self.repository.update_step(step)
                await self._emit("step.completed", task, step)

        if active_step is None:
            return None
        task.current_step_run_id = active_step.step_run_id
        self.repository.update_task(task)
        return active_step

    @staticmethod
    def _current_observed_step(observed_steps: list[dict]) -> dict:
        # 여러 observed step 중 실제 outcome을 적용할 실행 anchor 하나를 고른다.
        # 이미 완료된 선행 단계는 별도 StepRun으로 닫고, 이 단계에 최종 detail을 병합한다.
        return next(
            (
                observed_step
                for observed_step in observed_steps
                if str(observed_step.get("status") or "").strip().lower() in {"in_progress", "pending"}
            ),
            observed_steps[-1],
        )

    @staticmethod
    def _observed_steps_to_materialize(observed_steps: list[dict], current_step: dict) -> list[dict]:
        selected: list[dict] = []
        for observed_step in observed_steps:
            if observed_step is current_step:
                selected.append(observed_step)
                break
            if str(observed_step.get("status") or "").strip().lower() == "completed":
                selected.append(observed_step)
        if current_step not in selected:
            selected.append(current_step)
        return selected

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
                await self.step_handler.execute(
                    handler=handler,
                    task=task,
                    step=step,
                    resume_payload=resume_payload,
                    progress_sink=self._build_progress_sink(task=task, step=step),
                )
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
        task.status = task_status
        if task_is_terminal(task_status):
            step.ended_at = utc_now()
            task.ended_at = utc_now()
        self.repository.update_task(task)
        self.repository.update_step(step)
        await self._sync_todo_steps(task=task, handler=handler)

        if task_status == TaskStatus.COMPLETED:
            # 다음 plan step으로 넘어가더라도 현재 StepRun은 먼저 닫아야
            # realtime UI가 이전 단계를 계속 "진행 중"으로 보지 않는다.
            await self._emit("step.completed", task, step)

        if task_is_terminal(task_status):
            # todo_state(agent 내부 계획 상태)는 StepRun 경계가 아니므로 종료 시 남은 항목만 닫는다.
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

    def _build_progress_sink(self, *, task: TaskRun, step: StepRun | None):
        current_step = step

        async def sink(*, event_type: str, summary_message: str | None = None, payload: dict | None = None) -> None:
            nonlocal current_step
            if current_step is None:
                current_step = await self._materialize_progress_step(
                    task=task,
                    handler=self.tool_registry.get(task.entry_handler_key),
                    event_type=event_type,
                    payload=payload or {},
                )
            await self._emit(event_type, task, current_step, payload=payload, summary_message=summary_message)

        return sink

    async def _materialize_progress_step(self, *, task: TaskRun, handler, event_type: str, payload: dict) -> StepRun | None:
        """tool_call 관찰값에서 StepRun(LLM이 판단한 자연어 의미 단계)을 즉시 만든다.

        첫 provider 호출 전에는 StepRun을 만들지 않지만, assistant가 `step` runtime tool
        호출로 단계 제목/목표를 제안한 뒤에는 더 이상 완료까지 기다릴 이유가 없다.
        이 시점부터 후속 tool 이벤트를 같은 StepRun에 묶어 프론트가 진행 중 상태를 볼 수 있게 한다.
        """

        if event_type != "tool.started":
            return None
        if str(payload.get("tool_name") or payload.get("toolName") or "").strip() != "step":
            return None
        observed_steps = [item for item in payload.get("steps") or [] if isinstance(item, dict)]
        if not observed_steps:
            return None
        outcome = {
            "observed_steps": observed_steps,
            "summary_message": payload.get("title"),
            "detail_json": {},
        }
        materialized = await self._materialize_initial_observed_steps(task=task, handler=handler, outcome=outcome)
        if materialized is None:
            return None
        return materialized

    async def _emit(
        self,
        event_type: str,
        task: TaskRun,
        step: StepRun | None = None,
        payload: dict | None = None,
        summary_message: str | None = None,
    ) -> None:
        event_status = self._event_status(event_type=event_type, task=task, step=step)
        event_summary = summary_message if summary_message is not None else self._event_summary(event_type=event_type, task=task, step=step)
        event = build_task_event(
            event_type=event_type,
            task_run_id=task.task_run_id,
            step_run_id=step.step_run_id if step else None,
            producer="task_engine",
            status=event_status,
            summary_message=event_summary,
            payload=self._event_payload(event_type=event_type, step=step, payload=payload),
        )
        saved_event = self.repository.append_event(event)
        await self.broadcaster.publish(saved_event)

    @staticmethod
    def _event_status(*, event_type: str, task: TaskRun, step: StepRun | None = None) -> str:
        if step is not None and event_type.startswith("step."):
            return step.status
        if event_type.endswith(".completed"):
            return "COMPLETED"
        if event_type.endswith(".started"):
            return "RUNNING"
        if event_type.endswith(".failed"):
            return "FAILED"
        return task.status

    @staticmethod
    def _event_summary(*, event_type: str, task: TaskRun, step: StepRun | None = None) -> str | None:
        if event_type.startswith("step.") and step is not None:
            return step.summary_message or step.title or step.step_type
        return task.progress_summary

    @staticmethod
    def _event_payload(*, event_type: str, step: StepRun | None = None, payload: dict | None = None) -> dict:
        event_payload = dict(payload or {})
        if step is not None and event_type.startswith("step."):
            event_payload.setdefault("step_run_id", step.step_run_id)
            event_payload.setdefault("stepRunId", step.step_run_id)
            event_payload.setdefault("step_title", step.title)
            event_payload.setdefault("stepTitle", step.title)
            semantic_detail = (step.detail_json or {}).get("semanticDetail") or {}
            semantic_step = semantic_detail.get("semanticStep")
            if isinstance(semantic_step, str) and semantic_step.strip():
                event_payload.setdefault("semantic_step", semantic_step)
                event_payload.setdefault("semanticStep", semantic_step)
        return event_payload

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
