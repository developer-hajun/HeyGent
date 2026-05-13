from __future__ import annotations

import logging
from typing import Any

from app.clients.backend_iot_display import BackendIotDisplayClient, BackendIotDisplayClientError, BackendIotDisplayPayload
from app.domain.tasks.models import StepRun, TaskRun

logger = logging.getLogger(__name__)


class IotDisplayEventAdapter:
    """Task event를 작은 디바이스 표시 이벤트로 축약해 backend로 전달한다."""

    def __init__(self, backend_iot_display_client: BackendIotDisplayClient | None = None) -> None:
        self.backend_iot_display_client = backend_iot_display_client

    async def publish(
        self,
        *,
        event_type: str,
        task: TaskRun,
        step: StepRun | None,
        status: str | None,
        summary_message: str | None,
        payload: dict[str, Any],
    ) -> None:
        if self.backend_iot_display_client is None or not self.backend_iot_display_client.enabled:
            return

        device_payload = self._build_payload(
            event_type=event_type,
            task=task,
            step=step,
            status=status,
            summary_message=summary_message,
            payload=payload,
        )
        if device_payload is None:
            return

        try:
            await self.backend_iot_display_client.publish(device_payload)
        except BackendIotDisplayClientError:
            logger.warning("IoT display publish failed. event_type=%s task_run_id=%s", event_type, task.task_run_id)

    def _build_payload(
        self,
        *,
        event_type: str,
        task: TaskRun,
        step: StepRun | None,
        status: str | None,
        summary_message: str | None,
        payload: dict[str, Any],
    ) -> BackendIotDisplayPayload | None:
        user_id = self._owner_user_id(task)
        if user_id is None:
            return None
        session_id = str(task.session_key or (task.input_payload or {}).get("sessionId") or "").strip()
        if not session_id:
            return None

        mapping = self._map_event(event_type=event_type, step=step, status=status, payload=payload)
        if mapping is None:
            return None

        text = mapping["text"] or self._short_text(summary_message) or self._short_text(step.title if step else task.title) or "working"
        return BackendIotDisplayPayload(
            user_id=user_id,
            session_id=session_id,
            task_run_id=task.task_run_id,
            step_run_id=step.step_run_id if step is not None else None,
            type=mapping["type"],
            icon=mapping["icon"],
            text=text,
            text_key=mapping.get("text_key"),
            ttl_ms=mapping.get("ttl_ms"),
            priority=mapping.get("priority", 0),
            render_mode=mapping.get("render_mode", "AUTO"),
            status_kind=mapping.get("status_kind"),
            focus=mapping.get("focus", False),
        )

    def _map_event(self, *, event_type: str, step: StepRun | None, status: str | None, payload: dict[str, Any]):
        if event_type in {"task.created", "task.started"}:
            return self._mapping("STARTED", "START", "checking", "CHECKING_REQUEST", 2000, 80, "STARTED", True)
        if event_type in {"task.completed"}:
            return self._mapping("DONE", "SUCCESS", "done", "DONE_SUCCESS", 3000, 70, "SUCCESS", True, "SUCCESS")
        if event_type in {"task.failed"}:
            return self._mapping("FAILED", "ERROR", "failed", "FAILED", 5000, 70, "FAILED", True, "FAILURE")
        if event_type in {"task.canceled", "task.cancelled"}:
            return self._mapping("CANCELED", "CANCEL", "canceled", "CANCELED", 3000, 60, "CANCELED", True)
        if event_type in {"step.waiting"} or status in {"WAITING", "BLOCKED"}:
            return self._mapping("WAITING", "QUESTION", "waiting", "WAITING_INPUT", 0, 100, "WAITING", True, "WAITING")
        if event_type in {"step.failed"}:
            return self._mapping("FAILED", "ERROR", "failed", "FAILED", 5000, 70, "FAILED", True, "FAILURE")
        if event_type in {"step.completed"}:
            return self._mapping("STEP", "SUCCESS", "done", "STEP_DONE", 1500, 40, "RUNNING", False)
        if event_type in {"tool.started", "search.started"}:
            return self._tool_mapping(payload)
        if event_type in {"step.started", "step.created"}:
            return self._step_mapping(step=step, payload=payload)
        return None

    def _step_mapping(self, *, step: StepRun | None, payload: dict[str, Any]):
        semantic_key = self._semantic_key(step=step, payload=payload)
        if semantic_key in {"research", "search", "lookup"}:
            return self._mapping("STEP", "SEARCH", "searching", "SEARCHING", 2500, 40, "RUNNING", False)
        if semantic_key in {"write", "draft", "answer"}:
            return self._mapping("STEP", "WRITE", "writing", "WRITING_REPLY", 2500, 40, "RUNNING", False)
        if semantic_key in {"review", "verify"}:
            return self._mapping("STEP", "REVIEW", "reviewing", "REVIEWING", 2500, 40, "RUNNING", False)
        return self._mapping("STEP", "THINKING", self._short_text(payload.get("semanticStep")) or "working", "WORKING", 2500, 30, "RUNNING", False)

    def _tool_mapping(self, payload: dict[str, Any]):
        tool_name = str(payload.get("tool_name") or payload.get("toolName") or "").lower()
        if "search" in tool_name:
            return self._mapping("STEP", "SEARCH", "searching", "SEARCHING", 2500, 45, "RUNNING", False)
        if "http" in tool_name or "api" in tool_name or "web" in tool_name:
            return self._mapping("STEP", "TOOL", "http call", "HTTP_CALL", 2500, 45, "RUNNING", False)
        if "delegate" in tool_name:
            return self._mapping("STEP", "DELEGATE", "delegate", "DELEGATING", 2500, 45, "RUNNING", False)
        return self._mapping("STEP", "TOOL", "tool run", "TOOL_RUNNING", 2500, 40, "RUNNING", False)

    def _mapping(
        self,
        event_type: str,
        icon: str,
        text: str,
        text_key: str,
        ttl_ms: int,
        priority: int,
        status_kind: str,
        focus: bool,
        render_mode: str = "AUTO",
    ) -> dict[str, Any]:
        return {
            "type": event_type,
            "icon": icon,
            "text": text,
            "text_key": text_key,
            "ttl_ms": ttl_ms,
            "priority": priority,
            "status_kind": status_kind,
            "focus": focus,
            "render_mode": render_mode,
        }

    def _owner_user_id(self, task: TaskRun) -> int | None:
        task_input = task.input_payload or {}
        candidate = task_input.get("ownerUserId") or task_input.get("owner_user_id") or task.owner_key
        try:
            return int(str(candidate))
        except (TypeError, ValueError):
            return None

    def _semantic_key(self, *, step: StepRun | None, payload: dict[str, Any]) -> str:
        if isinstance(payload.get("semantic_key"), str):
            return str(payload["semantic_key"]).strip().lower()
        if step is None:
            return ""
        detail = step.detail_json or {}
        semantic = detail.get("semanticDetail") if isinstance(detail.get("semanticDetail"), dict) else {}
        return str(semantic.get("semanticKey") or step.step_type or "").strip().lower()

    def _short_text(self, value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = " ".join(value.strip().split())
        if not normalized:
            return None
        return normalized[:12]
