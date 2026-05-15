from __future__ import annotations

import logging
from typing import Any

from app.clients.backend_iot_display import BackendIotDisplayClient, BackendIotDisplayClientError, BackendIotDisplayPayload
from app.domain.tasks.models import StepRun, TaskRun

logger = logging.getLogger(__name__)


DEVICE_TEXT_MAX_CHARS = 8


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

        mapping = self._map_event(event_type=event_type, task=task, step=step, status=status, payload=payload)
        if mapping is None:
            return None

        text = (
            self._device_text(mapping["text"])
            or self._device_text(summary_message)
            or self._device_text(step.title if step else task.title)
            or "작업중"
        )
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

    def _map_event(
        self,
        *,
        event_type: str,
        task: TaskRun,
        step: StepRun | None,
        status: str | None,
        payload: dict[str, Any],
    ):
        if event_type in {"task.created", "task.started"}:
            return self._mapping(
                "STARTED",
                "START",
                self._checking_text(task=task, payload=payload),
                "CHECKING_REQUEST",
                2000,
                80,
                "STARTED",
                True,
            )
        if event_type in {"task.completed"}:
            return self._mapping("DONE", "SUCCESS", "성공!", "DONE_SUCCESS", 3000, 70, "SUCCESS", True, "SUCCESS")
        if event_type in {"task.failed"}:
            return self._mapping("FAILED", "ERROR", "답변 실패", "FAILED", 5000, 70, "FAILED", True, "FAILURE")
        if event_type in {"task.canceled", "task.cancelled"}:
            return self._mapping("CANCELED", "CANCEL", "취소됨", "CANCELED", 3000, 60, "CANCELED", True)
        if event_type in {"step.waiting"} or status in {"WAITING", "BLOCKED"}:
            waiting_text, text_key = self._waiting_text_and_key(task=task, step=step, payload=payload)
            return self._mapping("WAITING", "QUESTION", waiting_text, text_key, 0, 100, "WAITING", True, "WAITING")
        if event_type in {"step.failed"}:
            return self._mapping("FAILED", "ERROR", "실패함", "FAILED", 5000, 70, "FAILED", True, "FAILURE")
        if event_type in {"step.completed"}:
            return self._mapping("STEP", "SUCCESS", "단계 완료", "STEP_DONE", 1500, 40, "RUNNING", False)
        if event_type in {"tool.started", "search.started"}:
            return self._tool_mapping(payload)
        if event_type in {"tool.completed", "tool.result"}:
            return self._tool_completed_mapping(payload)
        if event_type in {"step.started", "step.created"}:
            return self._step_mapping(step=step, payload=payload)
        return None

    def _step_mapping(self, *, step: StepRun | None, payload: dict[str, Any]):
        operation_mapping = self._operation_mapping(step=step, payload=payload)
        if operation_mapping is not None:
            return operation_mapping

        agent_detail = self._record(payload.get("agentDetail")) or self._detail_record(step, "agentDetail")
        display_context = self._record(payload.get("displayContext"))
        if self._has_worker_context(agent_detail=agent_detail, display_context=display_context):
            return self._mapping("STEP", "DELEGATE", "위임중", "DELEGATING", 2500, 45, "RUNNING", False)

        semantic_key = self._semantic_key(step=step, payload=payload)
        if self._is_research_semantic(semantic_key):
            return self._mapping("STEP", "SEARCH", "자료 검색", "SEARCHING", 2500, 40, "RUNNING", False)
        if self._is_write_semantic(semantic_key):
            return self._mapping("STEP", "WRITE", "답변 작성", "WRITING_REPLY", 2500, 40, "RUNNING", False)
        if self._is_code_semantic(semantic_key):
            return self._mapping("STEP", "CODE", "코드 수정", "CODING", 2500, 40, "RUNNING", False)
        if self._is_review_semantic(semantic_key):
            return self._mapping("STEP", "REVIEW", "결과 검토", "REVIEWING", 2500, 40, "RUNNING", False)
        semantic_step = self._semantic_step(step=step, payload=payload)
        return self._mapping("STEP", "THINKING", self._device_text(semantic_step) or "작업중", "WORKING", 2500, 30, "RUNNING", False)

    def _tool_mapping(self, payload: dict[str, Any]):
        tool_name = self._tool_name(payload)
        context_text, context_key = self._contextual_tool_text(tool_name=tool_name, payload=payload)
        if context_text is not None:
            return self._mapping("STEP", "SEARCH", context_text, context_key, 2500, 45, "RUNNING", False)
        if self._is_message_tool(tool_name):
            return self._mapping("STEP", "SEND", "전송중", "SENDING_MESSAGE", 3000, 50, "RUNNING", False)
        if "search" in tool_name:
            return self._mapping("STEP", "SEARCH", "자료 검색", "SEARCHING", 2500, 45, "RUNNING", False)
        if "http" in tool_name or "api" in tool_name or "web" in tool_name:
            return self._mapping("STEP", "TOOL", "HTTP 호출", "HTTP_CALL", 2500, 45, "RUNNING", False)
        if "delegate" in tool_name or "session_agent" in tool_name:
            return self._mapping("STEP", "DELEGATE", "위임중", "DELEGATING", 2500, 45, "RUNNING", False)
        if "write_file" in tool_name or tool_name.endswith(".write"):
            return self._mapping("STEP", "WRITE", "파일 작성", "TOOL_RUNNING", 2500, 40, "RUNNING", False)
        if "read_file" in tool_name or tool_name.endswith(".read"):
            return self._mapping("STEP", "TOOL", "파일 읽기", "TOOL_RUNNING", 2500, 40, "RUNNING", False)
        if "terminal" in tool_name:
            return self._mapping("STEP", "TOOL", "터미널 실행", "TOOL_RUNNING", 2500, 40, "RUNNING", False)
        return self._mapping("STEP", "TOOL", "도구 실행", "TOOL_RUNNING", 2500, 40, "RUNNING", False)

    def _tool_completed_mapping(self, payload: dict[str, Any]):
        tool_name = self._tool_name(payload)
        if self._is_message_tool(tool_name):
            return self._mapping("STEP", "SUCCESS", "전송 완료", "STEP_DONE", 1500, 45, "RUNNING", False)
        return self._mapping("STEP", "SUCCESS", "단계 완료", "STEP_DONE", 1500, 35, "RUNNING", False)

    def _is_message_tool(self, tool_name: str) -> bool:
        normalized = tool_name.replace("_", ".").replace("-", ".")
        return "mattermost" in normalized or "send.message" in normalized or normalized.endswith(".send") or normalized == "send"

    def _checking_text(self, *, task: TaskRun, payload: dict[str, Any]) -> str:
        topic = self._topic_hint(task=task, payload=payload)
        if topic:
            if topic == "자료":
                return "자료 검색"
            return self._device_text(f"{topic} 확인") or "요청 확인"
        return "요청 확인"

    def _waiting_text_and_key(
        self,
        *,
        task: TaskRun,
        step: StepRun | None,
        payload: dict[str, Any],
    ) -> tuple[str, str]:
        approval_detail = self._record(payload.get("approvalDetail")) or self._detail_record(step, "approvalDetail")
        model_decision_detail = self._record(payload.get("modelDecisionDetail")) or self._detail_record(
            step,
            "modelDecisionDetail",
        )
        wait_payload = {}
        if isinstance(task.wait_payload, dict):
            wait_payload.update(task.wait_payload)
        if step is not None and isinstance(step.wait_payload, dict):
            wait_payload.update(step.wait_payload)
        if isinstance(payload.get("waitPayload"), dict):
            wait_payload.update(payload["waitPayload"])

        pending_tool = str(
            wait_payload.get("pending_tool_name")
            or wait_payload.get("tool_name")
            or payload.get("pending_tool_name")
            or "",
        ).strip()
        approval_requested = bool(
            (approval_detail or {}).get("approvalRequested")
            or (approval_detail or {}).get("requested")
            or wait_payload.get("approval_id")
            or "approval" in pending_tool.lower()
        )
        model_action = str((model_decision_detail or {}).get("action") or "").strip().lower()

        if approval_requested:
            return "승인 대기", "WAITING_APPROVAL"
        if model_action in {"ask_user", "request_input", "wait_user"}:
            return "입력 대기", "NEED_INPUT"
        return "입력 대기", "WAITING_INPUT"

    def _topic_hint(self, *, task: TaskRun, payload: dict[str, Any]) -> str | None:
        candidates = [
            payload.get("query"),
            payload.get("title"),
            payload.get("summary"),
            (task.input_payload or {}).get("query"),
            (task.input_payload or {}).get("message"),
            (task.input_payload or {}).get("userMessage"),
            (task.input_payload or {}).get("prompt"),
            task.title,
        ]
        for candidate in candidates:
            normalized = self._plain_text(candidate)
            if not normalized:
                continue
            lowered = normalized.lower()
            if "날씨" in normalized or "weather" in lowered:
                return "날씨"
            if "메타모스트" in normalized or "mattermost" in lowered:
                return "메시지"
            if "코드" in normalized or "code" in lowered:
                return "코드"
            if "파일" in normalized or "file" in lowered:
                return "파일"
            if "검색" in normalized or "search" in lowered:
                return "자료"
            if "노션" in normalized or "notion" in lowered:
                return "노션"
            if "메일" in normalized or "gmail" in lowered or "email" in lowered:
                return "메일"
            return self._device_text(self._strip_request_suffix(normalized))
        return None

    def _operation_mapping(self, *, step: StepRun | None, payload: dict[str, Any]):
        operation_detail = self._record(payload.get("operationDetail")) or self._detail_record(step, "operationDetail")
        operation = self._current_operation(operation_detail)
        if operation is None:
            return None

        kind = str(operation.get("kind") or operation.get("rawKind") or "").strip().lower()
        operation_text = " ".join(
            str(operation.get(key) or "").strip()
            for key in ("key", "title", "summary")
            if operation.get(key)
        ).lower()
        delegation_tokens = ("delegate", "worker", "agent", "위임", "에이전트")
        if kind in {"handoff", "delegate"} or any(token in operation_text for token in delegation_tokens):
            return self._mapping("STEP", "DELEGATE", "위임중", "DELEGATING", 2500, 45, "RUNNING", False)
        if kind == "summarize" or any(token in operation_text for token in ("summary", "summarize", "요약")):
            return self._mapping("STEP", "REVIEW", "요약중", "REVIEWING", 2500, 40, "RUNNING", False)
        if kind == "finalize" or any(token in operation_text for token in ("final", "finish", "마무리")):
            return self._mapping("STEP", "REVIEW", "마무리중", "REVIEWING", 2500, 40, "RUNNING", False)
        if kind == "prepare" or any(token in operation_text for token in ("prepare", "plan", "준비", "계획")):
            return self._mapping("STEP", "START", "요청 확인", "CHECKING_REQUEST", 2500, 35, "RUNNING", False)
        if kind == "execute":
            context_text, context_key = self._contextual_tool_text(tool_name=operation_text, payload=payload)
            if context_text is not None:
                return self._mapping("STEP", "SEARCH", context_text, context_key, 2500, 45, "RUNNING", False)
            if "http" in operation_text or "api" in operation_text:
                return self._mapping("STEP", "TOOL", "HTTP 호출", "HTTP_CALL", 2500, 45, "RUNNING", False)
        return None

    def _current_operation(self, operation_detail: dict[str, Any] | None) -> dict[str, Any] | None:
        operations = (operation_detail or {}).get("operations")
        if not isinstance(operations, list):
            return None
        candidates = [operation for operation in operations if isinstance(operation, dict)]
        if not candidates:
            return None
        for status in ("running", "waiting", "pending"):
            for operation in reversed(candidates):
                if str(operation.get("status") or "").strip().lower() == status:
                    return operation
        return candidates[-1]

    def _has_worker_context(
        self,
        *,
        agent_detail: dict[str, Any] | None,
        display_context: dict[str, Any] | None,
    ) -> bool:
        if (agent_detail or {}).get("workerSessionId"):
            return True
        actor_agent = (display_context or {}).get("actorAgent")
        if isinstance(actor_agent, dict) and str(actor_agent.get("kind") or "").lower() == "worker":
            return True
        delegated_agents = (display_context or {}).get("delegatedAgents")
        return isinstance(delegated_agents, list) and any(isinstance(agent, dict) for agent in delegated_agents)

    def _tool_name(self, payload: dict[str, Any]) -> str:
        direct = self._plain_text(payload.get("tool_name") or payload.get("toolName") or payload.get("name"))
        if direct:
            return direct.lower()
        operation_detail = self._record(payload.get("operationDetail"))
        operation = self._current_operation(operation_detail)
        if operation is None:
            return ""
        return " ".join(
            str(operation.get(key) or "").strip()
            for key in ("key", "title", "summary")
            if operation.get(key)
        ).lower()

    def _contextual_tool_text(self, *, tool_name: str, payload: dict[str, Any]) -> tuple[str | None, str | None]:
        topic = self._topic_hint_from_payload(payload)
        source = " ".join(value for value in (tool_name, topic or "") if value)
        lowered = source.lower()
        if "날씨" in source or "weather" in lowered:
            return "날씨 확인", "SEARCHING"
        if "노션" in source or "notion" in lowered:
            return "노션 확인", "TOOL_RUNNING"
        if "메일" in source or "gmail" in lowered or "email" in lowered:
            return "메일 확인", "TOOL_RUNNING"
        return None, None

    def _topic_hint_from_payload(self, payload: dict[str, Any]) -> str | None:
        for key in ("query", "title", "summary", "prompt", "userMessage", "message"):
            value = self._plain_text(payload.get(key))
            if value:
                lowered = value.lower()
                if "날씨" in value or "weather" in lowered:
                    return "날씨"
                if "노션" in value or "notion" in lowered:
                    return "노션"
                if "메일" in value or "gmail" in lowered or "email" in lowered:
                    return "메일"
                if "메타모스트" in value or "mattermost" in lowered:
                    return "메시지"
                if "검색" in value or "search" in lowered:
                    return "자료"
        return None

    def _strip_request_suffix(self, value: str) -> str:
        stripped = value.strip(" .!?。！？")
        for suffix in ("해줘", "해주세요", "알려줘", "찾아줘", "확인해줘", "검색해줘", "작성해줘", "요청", "확인"):
            if stripped.endswith(suffix):
                stripped = stripped[: -len(suffix)].strip()
        return stripped or value

    def _is_research_semantic(self, semantic_key: str) -> bool:
        return any(token in semantic_key for token in ("research", "search", "lookup", "browse", "web", "자료", "검색"))

    def _is_write_semantic(self, semantic_key: str) -> bool:
        return any(token in semantic_key for token in ("write", "draft", "answer", "compose", "response", "작성", "답변"))

    def _is_code_semantic(self, semantic_key: str) -> bool:
        return any(token in semantic_key for token in ("code", "coding", "patch", "implement", "코드", "구현", "수정"))

    def _is_review_semantic(self, semantic_key: str) -> bool:
        return any(token in semantic_key for token in ("review", "verify", "validate", "check", "검토", "확인"))

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
        semantic_payload = self._record(payload.get("semanticDetail"))
        if semantic_payload is not None:
            return str(semantic_payload.get("semanticKey") or "").strip().lower()
        if step is None:
            return ""
        detail = step.detail_json or {}
        semantic = detail.get("semanticDetail") if isinstance(detail.get("semanticDetail"), dict) else {}
        return str(semantic.get("semanticKey") or step.step_type or "").strip().lower()

    def _semantic_step(self, *, step: StepRun | None, payload: dict[str, Any]) -> str | None:
        semantic_payload = self._record(payload.get("semanticDetail"))
        if semantic_payload is not None:
            value = self._plain_text(semantic_payload.get("semanticStep") or semantic_payload.get("step"))
            if value:
                return value
        value = self._plain_text(payload.get("semanticStep"))
        if value:
            return value
        if step is None:
            return None
        semantic = self._detail_record(step, "semanticDetail")
        value = self._plain_text((semantic or {}).get("semanticStep") or (semantic or {}).get("step"))
        return value or step.title

    def _detail_record(self, step: StepRun | None, key: str) -> dict[str, Any] | None:
        if step is None:
            return None
        detail = step.detail_json or {}
        return self._record(detail.get(key))

    def _record(self, value: Any) -> dict[str, Any] | None:
        return value if isinstance(value, dict) else None

    def _plain_text(self, value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = " ".join(value.strip().split())
        return normalized or None

    def _device_text(self, value: Any) -> str | None:
        normalized = self._plain_text(value)
        if not normalized:
            return None
        return normalized[:DEVICE_TEXT_MAX_CHARS].strip()
