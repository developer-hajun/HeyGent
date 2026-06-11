"""TaskOutcomeMixin: 핸들러 실행 결과 적용 및 실패 처리."""
from __future__ import annotations

import re
from typing import Any

from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus
from app.core.time import utc_now
from app.api.http.device_tokens import get_fcm_tokens
from app.domain.notifications.fcm_sender import send_chat_notification
from app.domain.orchestration.policies import (
    ensure_step_transition,
    ensure_task_transition,
    semantic_lifecycle_for_status,
    step_is_terminal,
    task_is_terminal,
)
from app.domain.orchestration.runtime_planning.todo_state import (
    build_task_todo_payload,
    cancel_incomplete_task_todo_items,
)
from app.domain.tasks.detail import (
    build_model_decision_detail,
    build_semantic_step_detail,
    infer_semantic_status,
    merge_step_detail,
    semantic_key_of,
)

import logging

logger = logging.getLogger(__name__)


class TaskOutcomeMixin:
    """TaskEngine의 step/task outcome 적용, 취소, 실패 처리 담당."""

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
                },
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
        redacted_message = TaskOutcomeMixin._redact_sensitive_error_text(compact_message)
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

    async def _apply_task_outcome_without_step(self, *, task: Any, outcome: dict) -> Any:
        await self._ensure_skill_work_link_from_outcome(task=task, outcome=outcome)
        task_status = outcome["task_status"]
        if task_status == TaskStatus.WAITING:
            task_status = TaskStatus.FAILED
            outcome = {
                **outcome,
                "task_status": TaskStatus.FAILED,
                "error_message": "StepRun declaration is required before approval-gated tool execution.",
                "summary_message": "승인 필요 도구 실행 전에 현재 단계를 먼저 선언해야 합니다.",
            }

        ensure_task_transition(task.status, task_status)
        task.status = task_status
        task.current_step_run_id = None
        task.result_payload = outcome.get("result_payload", task.result_payload)
        task.todo_state = dict(outcome.get("todo_state") or task.todo_state)
        task.wait_payload = outcome.get("wait_payload", {})
        task.error_message = outcome.get("error_message")
        task.progress_summary = outcome.get("summary_message")
        task.revision += 1
        if task_is_terminal(task_status):
            task.ended_at = utc_now()
            task.todo_state = build_task_todo_payload(cancel_incomplete_task_todo_items(task.todo_state))
        self.repository.update_task(task)

        if task_status == TaskStatus.COMPLETED:
            await self._emit("task.completed", task, payload=task.result_payload)
            try:
                if task.session_key:
                    for fcm_token in get_fcm_tokens(str(task.owner_key)):
                        send_chat_notification(fcm_token, session_id=task.session_key, content="")
                    logger.info(f"FCM 발송 완료: owner={task.owner_key} session={task.session_key}")
                else:
                    logger.debug(f"FCM 스킵: token={bool(fcm_token)} session={task.session_key}")
            except Exception as e:
                logger.warning(f"FCM 발송 실패 (무시): {e}")
            return task

        if task_status == TaskStatus.FAILED:
            await self._emit("task.failed", task, payload={"error_message": task.error_message})
            return task

        if task_status == TaskStatus.CANCELED:
            await self._emit("task.canceled", task)
            return task

        await self._emit("task.updated", task)
        return task

    async def _apply_outcome(self, *, task: Any, step: Any, handler: Any, outcome: dict) -> Any:
        outcome = await self.delegate_runtime.apply(task=task, step=step, outcome=outcome, repository=self.repository)
        outcome = self.outcome_inspector.inspect(step=step, outcome=outcome)
        await self._ensure_skill_work_link_from_outcome(task=task, outcome=outcome)
        task_status = outcome["task_status"]
        step_status = outcome["step_status"]
        was_step_completed = step.status == StepStatus.COMPLETED
        ensure_task_transition(task.status, task_status)
        step_already_terminal = step_is_terminal(step.status)
        preserve_terminal_step = (
            task_status == TaskStatus.COMPLETED
            and step_status == StepStatus.COMPLETED
            and step_already_terminal
            and step.status != step_status
        )
        if not preserve_terminal_step:
            ensure_step_transition(step.status, step_status)

        if not preserve_terminal_step:
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
                semantic_step=(step.detail_json.get("semanticDetail") or {}).get("semanticStep")
                or step.title
                or step.step_type,
                semantic_goal=(step.detail_json.get("semanticDetail") or {}).get("goal")
                or step.title
                or step.step_type,
                lifecycle=semantic_lifecycle,
                status=infer_semantic_status(lifecycle=semantic_lifecycle, operation_detail=step.detail_json.get("operationDetail")),
            ),
        )
        step.summary_message = outcome.get("summary_message")
        task.status = task_status
        if task_is_terminal(task_status) and not preserve_terminal_step:
            step.ended_at = utc_now()
            task.ended_at = utc_now()
        elif task_is_terminal(task_status):
            task.ended_at = utc_now()
        self.repository.update_task(task)
        self.repository.update_step(step)
        await self._sync_todo_steps(task=task, handler=handler)

        if task_status == TaskStatus.COMPLETED and not was_step_completed and not preserve_terminal_step:
            await self._emit("step.completed", task, step)

        if task_is_terminal(task_status):
            task.todo_state = build_task_todo_payload(cancel_incomplete_task_todo_items(task.todo_state))
            self.repository.update_task(task)
            await self._sync_todo_steps(task=task, handler=handler)
            await self._cancel_incomplete_noncurrent_steps(task=task, current_step=step)

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
            try:
                if task.session_key:
                    for fcm_token in get_fcm_tokens(str(task.owner_key)):
                        send_chat_notification(fcm_token, session_id=task.session_key, content="")
            except Exception:
                pass
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

    async def _cancel_incomplete_noncurrent_steps(self, *, task: Any, current_step: Any) -> None:
        now = utc_now()
        for candidate in self.repository.list_steps(task.task_run_id):
            if candidate.step_run_id == current_step.step_run_id or step_is_terminal(candidate.status):
                continue
            ensure_step_transition(candidate.status, StepStatus.CANCELED)
            candidate.status = StepStatus.CANCELED
            candidate.ended_at = candidate.ended_at or now
            candidate.summary_message = candidate.summary_message or "작업 종료로 실행되지 않음"
            candidate.detail_json = merge_step_detail(
                candidate.detail_json,
                build_semantic_step_detail(
                    step_run_id=candidate.step_run_id,
                    semantic_key=semantic_key_of(candidate.detail_json) or candidate.step_type,
                    semantic_step=(candidate.detail_json.get("semanticDetail") or {}).get("semanticStep")
                    or candidate.title
                    or candidate.step_type,
                    semantic_goal=(candidate.detail_json.get("semanticDetail") or {}).get("goal")
                    or candidate.title
                    or candidate.step_type,
                    lifecycle="canceled",
                    status=infer_semantic_status(lifecycle="canceled", operation_detail=candidate.detail_json.get("operationDetail")),
                ),
            )
            self.repository.update_step(candidate)
            await self._emit("step.canceled", task, candidate)
