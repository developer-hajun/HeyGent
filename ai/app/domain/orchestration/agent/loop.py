from __future__ import annotations

import json
import logging

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
)
from app.domain.orchestration.runtime_planning import (
    Planner,
)
from app.domain.orchestration.runtime_planning.todo_state import (
    build_task_todo_payload,
    cancel_incomplete_task_todo_items,
)
from app.domain.orchestration.result_inspector import OutcomeInspector
from app.domain.session.sessions.transcript_store import TranscriptStore
from app.domain.tasks.detail import (
    build_semantic_step_detail,
    infer_semantic_status,
    merge_step_detail,
    semantic_key_of,
)
from app.domain.tasks.repository import TaskRepository
from app.domain.tasks.models import StepRun, TaskRun
from app.domain.orchestration.agent.loop_parts.iot_publisher import IotPublisher
from app.domain.orchestration.agent.loop_parts.event_broadcaster import EventBroadcaster
from app.domain.orchestration.agent.loop_parts.work_link_mixin import WorkLinkMixin
from app.domain.orchestration.agent.loop_parts.task_outcome_mixin import TaskOutcomeMixin
from app.domain.orchestration.agent.loop_parts.progress_sink_mixin import ProgressSinkMixin
from app.domain.orchestration.agent.loop_parts.delegate_executor_mixin import DelegateExecutorMixin
from app.domain.orchestration.agent.loop_parts.session_agent_mixin import SessionAgentMixin
from app.domain.orchestration.agent.loop_parts.event_emit_mixin import EventEmitMixin


logger = logging.getLogger(__name__)


class TaskEngine(
    WorkLinkMixin,
    TaskOutcomeMixin,
    ProgressSinkMixin,
    DelegateExecutorMixin,
    SessionAgentMixin,
    EventEmitMixin,
):
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
        work_repository=None,
        agent_repository=None,
        skill_repository=None,
        settings=None,
        iot_display_adapter=None,
    ) -> None:
        self.repository = repository
        self.broadcaster = broadcaster
        self.approval_service = approval_service
        self.child_session_launcher = child_session_launcher
        self.planner = planner
        self.tool_registry = tool_registry
        self.session_store = session_store
        self.work_repository = work_repository
        self.agent_repository = agent_repository
        self.skill_repository = skill_repository
        self.settings = settings
        self.iot_display_adapter = iot_display_adapter
        self.approval_runtime = ApprovalRuntime()
        self.delegate_runtime = DelegateRuntime(child_session_launcher, session_store=session_store)
        self.outcome_inspector = OutcomeInspector()
        self.step_handler = StepHandler()
        self._iot_publisher = IotPublisher(iot_display_adapter) if iot_display_adapter is not None else None
        self._event_broadcaster = EventBroadcaster(broadcaster, iot_publisher=self._iot_publisher)

    async def run(self, *, task: TaskRun, handler) -> TaskRun:
        saved = self.repository.create_direct_task(task)
        await self._emit("task.created", saved)
        return await self._execute_initial(task=saved, handler=handler, resume_payload=None)

    async def enqueue_pending(self, *, task: TaskRun) -> TaskRun:
        saved = self.repository.create_pending_task(task)
        await self._emit("task.created", saved)
        return saved

    async def run_claimed(self, *, task: TaskRun, handler) -> TaskRun:
        latest = self.repository.get_task(task.task_run_id) or task
        queue_status = str(getattr(latest, "queue_status", "") or "")
        claim_owner = str(getattr(latest, "claim_owner", "") or "")
        if queue_status not in {"claimed", "running"} or not claim_owner:
            raise RuntimeError(f"TaskRun is not claimed by a supervisor worker: {task.task_run_id}")
        return await self._execute_initial(task=task, handler=handler, resume_payload=None)

    async def _execute_initial(self, *, task: TaskRun, handler, resume_payload: dict | None, token_sink=None) -> TaskRun:
        ensure_task_transition(task.status, TaskStatus.RUNNING)
        task.status = TaskStatus.RUNNING
        task.started_at = task.started_at or utc_now()
        task.wait_payload = {}
        step = self.planner.materialize_runtime_step(
            task=task,
            handler=handler,
            input_payload=task.input_payload,
            step_order=1,
        )
        ensure_step_transition(step.status, StepStatus.RUNNING)
        step.status = StepStatus.RUNNING
        step.started_at = step.started_at or task.started_at
        task.current_step_run_id = step.step_run_id
        self.repository.create_step(step)
        self.repository.update_task(task)
        self._touch_linked_work_run(task)
        await self._emit("task.started", task)
        await self._emit("step.created", task, step)
        await self._emit("step.started", task, step)

        try:
            progress_sink = self._build_progress_sink(task=task, step=step)
            progress_sink.token_sink = token_sink
            outcome = normalize_handler_outcome(
                await self.step_handler.execute(
                    handler=handler,
                    task=task,
                    step=step,
                    resume_payload=resume_payload,
                    progress_sink=progress_sink,
                    delegate_executor=self._build_delegate_executor(task=task, handler=handler, progress_sink=progress_sink),
                    session_agent_executor=self._build_session_agent_work_executor(task=task, handler=handler, progress_sink=progress_sink),
                )
            )
        except Exception as error:
            outcome = self._build_handler_failure_outcome(error)
        live_step = self.repository.get_step(task.current_step_run_id) if task.current_step_run_id else None
        return await self._apply_outcome(task=task, step=live_step or step, handler=handler, outcome=outcome)

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
        handler = self.tool_registry.resolve()

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
        self._touch_linked_work_run(task)
        await self._emit("task.started", task)
        await self._emit("step.started", task, step)

        try:
            progress_sink = self._build_progress_sink(task=task, step=step)
            outcome = normalize_handler_outcome(
                await self.step_handler.execute(
                    handler=handler,
                    task=task,
                    step=step,
                    resume_payload=resume_payload,
                    progress_sink=progress_sink,
                    delegate_executor=self._build_delegate_executor(task=task, handler=handler, progress_sink=progress_sink),
                    session_agent_executor=self._build_session_agent_work_executor(task=task, handler=handler, progress_sink=progress_sink),
                )
            )
        except Exception as error:
            outcome = self._build_handler_failure_outcome(error)
        return await self._apply_outcome(task=task, step=step, handler=handler, outcome=outcome)


def _work_status_label(status: str) -> str:
    return {
        "todo": "대기",
        "in_progress": "진행 중",
        "in_review": "검토 중",
        "blocked": "차단됨",
        "done": "완료",
        "cancelled": "취소됨",
    }.get(str(status or ""), str(status or ""))
