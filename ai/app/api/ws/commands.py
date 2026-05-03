from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime
import logging
from typing import Any, Awaitable, Callable

from pydantic import BaseModel

from app.contracts.task.task_status import TaskStatus
from app.core.time import utc_now
from app.core.utils.ids import new_id
logger = logging.getLogger(__name__)

_PUBLIC_SESSION_SOURCE = "api.session"
_TASK_TRANSCRIPT_SOURCE = "agent.loop"
_ACTIVE_TASK_STATUSES = [status.value for status in (TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.WAITING, TaskStatus.BLOCKED)]
_TERMINAL_TASK_STATUSES = {status.value for status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED)}


class WebSocketCommandError(Exception):
    """command.error frame으로 변환할 수 있는 WebSocket protocol 오류다."""

    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


@dataclass(slots=True)
class WebSocketAuthContext:
    """인증된 WebSocket 연결이 살아 있는 동안만 유지되는 메모리 컨텍스트다.

    access_token은 backend 호출이 필요한 후속 command에서만 메모리로 참조할 수 있다.
    DB, event, projection, detail_json에는 절대 넣지 않는다.
    """

    user_id: str
    access_token: str
    workspace_key: str | None = None
    scopes: list[str] | None = None
    token_expires_at: str | None = None
    scope_expires_at: str | None = None


@dataclass(slots=True)
class WebSocketCommandContext:
    websocket: Any
    auth: WebSocketAuthContext
    gateway_session_id: str
    session_service: Any
    send_json: Callable[[dict[str, Any]], Awaitable[None]]
    background_tasks: set[asyncio.Task]


@dataclass(slots=True)
class WebSocketBackgroundContext:
    """연결 종료 뒤에도 실행될 수 있는 작업용 컨텍스트다.

    background task는 WebSocket close 이후까지 남을 수 있으므로 accessToken을 참조하지 않는다.
    """

    websocket: Any
    send_json: Callable[[dict[str, Any]], Awaitable[None]]


class WebSocketCommandRouter:
    """인증 이후 WebSocket command/query를 처리한다.

    기존 gateway는 auth.start/auth.ok/subscribe.task/ping을 담당하고,
    이 라우터는 requestId가 있는 command/query 응답을 같은 연결로 되돌린다.
    """

    def __init__(self) -> None:
        self._accepted_messages: dict[tuple[str, str, str], dict[str, Any]] = {}
        self._accepted_resumes: dict[tuple[str, str], dict[str, Any]] = {}
        self._accepted_cancels: dict[tuple[str, str], dict[str, Any]] = {}

    async def handle(self, message: dict[str, Any], context: WebSocketCommandContext) -> bool:
        message_type = message.get("type")
        if not isinstance(message_type, str):
            return False

        handlers = {
            "session.list": self._session_list,
            "session.messages.list": self._session_messages_list,
            "session.message.create": self._session_message_create,
            "taskRuns.active.list": self._task_runs_active_list,
            "taskRun.snapshot.get": self._task_run_snapshot_get,
            "taskRun.events.replay": self._task_run_events_replay,
            "taskRun.resume": self._task_run_resume,
            "taskRun.cancel": self._task_run_cancel,
        }
        handler = handlers.get(message_type)
        if handler is None:
            return False

        request_id = message.get("requestId")
        payload = message.get("payload") or {}
        if not isinstance(payload, dict):
            await self._send_error(context, request_id, "invalid_payload", "payload must be an object")
            return True

        try:
            response_type, response_payload = await handler(payload, context)
        except WebSocketCommandError as error:
            await self._send_error(context, request_id, error.code, error.message, retryable=error.retryable)
            return True
        except Exception:
            logger.exception("WebSocket command 처리 중 예외가 발생했습니다: %s", message_type)
            await self._send_error(context, request_id, "internal_error", "command failed", retryable=True)
            return True

        await self._send_result(context, response_type, request_id, response_payload)
        return True

    async def send_unknown_command_error(self, message: dict[str, Any], context: WebSocketCommandContext) -> None:
        message_type = message.get("type")
        request_id = message.get("requestId")
        await self._send_error(
            context,
            request_id,
            "unknown_command",
            f"unsupported command type: {message_type}",
        )

    async def _session_list(self, payload: dict[str, Any], context: WebSocketCommandContext) -> tuple[str, dict[str, Any]]:
        page = _positive_int(payload.get("page"), default=1, maximum=10_000)
        page_size = _positive_int(payload.get("pageSize", payload.get("page_size")), default=20, maximum=50)
        offset = (page - 1) * page_size
        session_store = context.websocket.app.state.session_store
        sessions = [
            session
            for session in session_store.list_sessions(user_id=context.auth.user_id, limit=10_000, offset=0)
            if _is_public_session(session)
        ]
        selected = sessions[offset : offset + page_size]
        return (
            "session.list.result",
            {
                "items": [_public_session_payload(session) for session in selected],
                "page": page,
                "page_size": page_size,
                "total_count": len(sessions),
                "has_previous": page > 1,
                "has_next": offset + len(selected) < len(sessions),
            },
        )

    async def _session_messages_list(self, payload: dict[str, Any], context: WebSocketCommandContext) -> tuple[str, dict[str, Any]]:
        session_id = _required_str(payload, "sessionId", "session_id")
        after_message_id = _optional_int(payload.get("afterMessageId", payload.get("after_message_id")))
        limit = _positive_int(payload.get("limit"), default=100, maximum=500)
        session = _get_public_session(context, session_id)
        _ensure_owner(context, session.get("user_id"))
        messages = context.websocket.app.state.session_store.list_messages(session_id)
        if after_message_id is not None:
            messages = [message for message in messages if int(message.get("id") or 0) > after_message_id]
        items = [_message_payload(message) for message in messages[:limit]]
        return (
            "session.messages.result",
            {
                "session_id": session_id,
                "after_message_id": after_message_id,
                "limit": limit,
                "total_count": len(items),
                "next_after_message_id": items[-1]["id"] if items else None,
                "items": items,
            },
        )

    async def _session_message_create(self, payload: dict[str, Any], context: WebSocketCommandContext) -> tuple[str, dict[str, Any]]:
        content = _required_str(payload, "content")
        client_message_id = _required_str(payload, "clientMessageId", "client_message_id")
        session_id = _optional_str(payload.get("sessionId", payload.get("session_id")))
        model = _optional_str(payload.get("model"))
        input_payload = payload.get("inputPayload", payload.get("input_payload")) or {}
        if not isinstance(input_payload, dict):
            raise WebSocketCommandError("invalid_payload", "inputPayload must be an object")

        idempotency_key = (context.auth.user_id, session_id or "", client_message_id)
        existing = self._accepted_messages.get(idempotency_key)
        if existing is not None:
            return "session.message.accepted", dict(existing)

        if session_id:
            session = _get_public_session(context, session_id)
            _ensure_owner(context, session.get("user_id"))
        else:
            session = _create_public_session(context, content=content, model=model)
            session_id = str(session["id"])

        session_store = context.websocket.app.state.session_store
        user_message_id = session_store.append_message(
            session_id=session_id,
            role="user",
            content=content,
            metadata={
                "source": _PUBLIC_SESSION_SOURCE,
                # clientMessageId는 재전송/낙관적 UI 병합을 추적하기 위한 idempotency 키다.
                # accessToken과 달리 비밀값이 아니며, durable 저장되어도 보안 경계가 흔들리지 않는다.
                "client_message_id": client_message_id,
            },
        )
        transcript_session_id = _create_task_transcript_session(
            session_store,
            session_id=session_id,
            owner_key=context.auth.user_id,
            title=session.get("title") or content[:120],
            model=model,
        )
        task_input = dict(input_payload)
        if model and not task_input.get("model"):
            task_input["model"] = model
        task_input["prompt"] = content
        task_input["transcript_session_id"] = transcript_session_id
        # token memory context는 durable payload에 넣지 않는다. backend 호출이 필요해지면
        # context.auth.access_token에서만 꺼내 쓰도록 경계를 고정한다.

        handler = context.websocket.app.state.tool_registry.resolve(intent_type=payload.get("intentType", payload.get("intent_type", "agent.loop")))
        task = context.websocket.app.state.task_engine.planner.materialize_task(
            owner_key=context.auth.user_id,
            session_key=session_id,
            input_payload=task_input,
            handler=handler,
        )
        context.websocket.app.state.repository.create_task(task)
        context.session_service.subscribe_task(
            session_id=context.gateway_session_id,
            websocket=context.websocket,
            task_run_id=task.task_run_id,
        )

        accepted = {
            "session_id": session_id,
            "user_message_id": user_message_id,
            "assistant_message_id": None,
            "task_run_id": task.task_run_id,
            "status": task.status,
            "client_message_id": client_message_id,
        }
        self._accepted_messages[idempotency_key] = accepted

        background_context = WebSocketBackgroundContext(websocket=context.websocket, send_json=context.send_json)
        background_task = asyncio.create_task(
            self._run_created_message_task(
                context=background_context,
                session_id=session_id,
                user_message_id=user_message_id,
                task=task,
                handler=handler,
            )
        )
        context.background_tasks.add(background_task)
        background_task.add_done_callback(context.background_tasks.discard)
        return "session.message.accepted", dict(accepted)

    async def _task_runs_active_list(self, payload: dict[str, Any], context: WebSocketCommandContext) -> tuple[str, dict[str, Any]]:
        session_id = _optional_str(payload.get("sessionId", payload.get("session_id")))
        repository = context.websocket.app.state.repository
        projection = getattr(context.websocket.app.state, "task_projection_store", None)
        items_by_task_run_id: dict[str, dict[str, Any]] = {}

        if projection is not None and session_id:
            for task_run_id in projection.list_active_task_ids(session_key=session_id):
                task = projection.get_task_snapshot(task_run_id)
                if task is None or str(task.owner_key) != str(context.auth.user_id):
                    continue
                steps = _projection_steps(projection, task.task_run_id)
                items_by_task_run_id[task.task_run_id] = _active_task_payload(task, steps, source="active", repository=repository)

        total = repository.count_tasks_by_statuses(_ACTIVE_TASK_STATUSES, session_key=session_id)
        for task in repository.list_tasks_by_statuses(_ACTIVE_TASK_STATUSES, session_key=session_id, limit=max(total, 1), offset=0):
            if task.task_run_id in items_by_task_run_id or str(task.owner_key) != str(context.auth.user_id):
                continue
            items_by_task_run_id[task.task_run_id] = _active_task_payload(
                task,
                repository.list_steps(task.task_run_id),
                source="active",
                repository=repository,
            )
        return (
            "taskRuns.active.result",
            {
                "session_id": session_id,
                "items": list(items_by_task_run_id.values()),
                "total_count": len(items_by_task_run_id),
            },
        )

    async def _task_run_snapshot_get(self, payload: dict[str, Any], context: WebSocketCommandContext) -> tuple[str, dict[str, Any]]:
        task_run_id = _required_str(payload, "taskRunId", "task_run_id")
        include_steps = bool(payload.get("includeSteps", payload.get("include_steps", True)))
        include_flow = bool(payload.get("includeFlow", payload.get("include_flow", False)))
        repository = context.websocket.app.state.repository
        task = repository.get_task(task_run_id)
        if task is None:
            raise WebSocketCommandError("not_found", "task not found")
        _ensure_owner(context, task.owner_key)
        steps = repository.list_steps(task_run_id) if include_steps or include_flow else []
        snapshot = {
            "task": _jsonable(task),
            "pending_approval": _pending_approval_payload(repository.get_open_approval(task_run_id)),
        }
        if include_steps:
            snapshot["steps"] = [_jsonable(step) for step in steps]
        if include_flow:
            snapshot["flow"] = {
                "task_run_id": task.task_run_id,
                "current_step_run_id": task.current_step_run_id,
                "nodes": [_jsonable(step) for step in steps],
                "edges": [
                    {"from_step_run_id": previous.step_run_id, "to_step_run_id": current.step_run_id, "relation": "next"}
                    for previous, current in zip(steps, steps[1:])
                ],
            }
        return "taskRun.snapshot.result", snapshot

    async def _task_run_events_replay(self, payload: dict[str, Any], context: WebSocketCommandContext) -> tuple[str, dict[str, Any]]:
        task_run_id = _required_str(payload, "taskRunId", "task_run_id")
        after_sequence = _optional_int(payload.get("afterSequence", payload.get("after_sequence")))
        limit = _positive_int(payload.get("limit"), default=200, maximum=500)
        repository = context.websocket.app.state.repository
        task = repository.get_task(task_run_id)
        if task is None:
            raise WebSocketCommandError("not_found", "task not found")
        _ensure_owner(context, task.owner_key)

        projection = getattr(context.websocket.app.state, "task_projection_store", None)
        retention_exceeded = False
        events: list[dict[str, Any]] = []
        if projection is not None:
            events = projection.list_recent_events(task_run_id)
            if after_sequence is not None:
                events = [event for event in events if int(event.get("sequence") or 0) > after_sequence]
            events = events[:limit]
            if after_sequence is not None and not events and projection.get_latest_sequence(task_run_id) is not None:
                retention_exceeded = projection.get_latest_sequence(task_run_id) > after_sequence

        if not events:
            stored_events = repository.list_events(task_run_id)
            if after_sequence is not None:
                stored_events = [event for event in stored_events if int(event.sequence or 0) > after_sequence]
            events = [_jsonable(event) for event in stored_events[:limit]]

        latest_sequence = max((int(event.get("sequence") or 0) for event in events), default=None)
        return (
            "taskRun.events.replay.result",
            {
                "task_run_id": task_run_id,
                "events": events,
                "latest_sequence": latest_sequence,
                "retention_exceeded": retention_exceeded,
            },
        )

    async def _task_run_resume(self, payload: dict[str, Any], context: WebSocketCommandContext) -> tuple[str, dict[str, Any]]:
        task_run_id = _required_str(payload, "taskRunId", "task_run_id")
        approval_id = _required_str(payload, "approvalId", "approval_id")
        command_id = _required_str(payload, "approvalResponseId", "approval_response_id", "clientCommandId", "client_command_id")
        resume_payload = payload.get("payload") or {}
        if not isinstance(resume_payload, dict):
            raise WebSocketCommandError("invalid_payload", "payload.payload must be an object")
        accepted_key = (task_run_id, command_id)
        existing = self._accepted_resumes.get(accepted_key)
        if existing is not None:
            return "taskRun.resume.accepted", dict(existing)

        task = context.websocket.app.state.repository.get_task(task_run_id)
        if task is None:
            raise WebSocketCommandError("not_found", "task not found")
        _ensure_owner(context, task.owner_key)
        if task.status != TaskStatus.WAITING:
            raise WebSocketCommandError("conflict", "task is not waiting")

        accepted = {
            "task_run_id": task_run_id,
            "approval_id": approval_id,
            "client_command_id": command_id,
        }
        self._accepted_resumes[accepted_key] = accepted
        background_task = asyncio.create_task(
            self._run_resume_task(
                context=WebSocketBackgroundContext(websocket=context.websocket, send_json=context.send_json),
                task_run_id=task_run_id,
                approval_id=approval_id,
                payload=resume_payload,
            )
        )
        context.background_tasks.add(background_task)
        background_task.add_done_callback(context.background_tasks.discard)
        return "taskRun.resume.accepted", dict(accepted)

    async def _task_run_cancel(self, payload: dict[str, Any], context: WebSocketCommandContext) -> tuple[str, dict[str, Any]]:
        task_run_id = _required_str(payload, "taskRunId", "task_run_id")
        command_id = _required_str(payload, "clientCommandId", "client_command_id")
        accepted_key = (task_run_id, command_id)
        existing = self._accepted_cancels.get(accepted_key)
        if existing is not None:
            return "taskRun.cancel.accepted", dict(existing)

        task = context.websocket.app.state.repository.get_task(task_run_id)
        if task is None:
            raise WebSocketCommandError("not_found", "task not found")
        _ensure_owner(context, task.owner_key)
        if task.status != TaskStatus.WAITING:
            raise WebSocketCommandError("conflict", "task is not waiting")

        accepted = {"task_run_id": task_run_id, "client_command_id": command_id}
        self._accepted_cancels[accepted_key] = accepted
        background_task = asyncio.create_task(
            self._run_cancel_task(
                context=WebSocketBackgroundContext(websocket=context.websocket, send_json=context.send_json),
                task_run_id=task_run_id,
            )
        )
        context.background_tasks.add(background_task)
        background_task.add_done_callback(context.background_tasks.discard)
        return "taskRun.cancel.accepted", dict(accepted)

    async def _run_created_message_task(self, *, context: WebSocketBackgroundContext, session_id: str, user_message_id: int, task: Any, handler: Any) -> None:
        try:
            # accepted는 "최종 답변 완료"가 아니라 durable 접수다.
            # task.created 이후부터는 기존 Task Engine 이벤트가 같은 구독 topic으로 흘러간다.
            await context.websocket.app.state.task_engine._emit("task.created", task)
            completed_task = await context.websocket.app.state.task_engine._execute_initial(
                task=task,
                handler=handler,
                resume_payload=None,
            )
            content = _assistant_content_from_task(completed_task)
            assistant_message_id = context.websocket.app.state.session_store.append_message(
                session_id=session_id,
                role="assistant",
                content=content,
                metadata={
                    "source": _PUBLIC_SESSION_SOURCE,
                    "task_run_id": completed_task.task_run_id,
                    "status": completed_task.status,
                    "user_message_id": user_message_id,
                },
                finish_reason="stop" if completed_task.status in _TERMINAL_TASK_STATUSES else None,
            )
            await context.send_json(
                _event_frame(
                    "session.message.completed",
                    {
                        "session_id": session_id,
                        "message_id": assistant_message_id,
                        "content": content,
                        "task_run_id": completed_task.task_run_id,
                        "status": completed_task.status,
                    },
                )
            )
        except Exception:
            logger.exception("session.message.create background 실행에 실패했습니다.")

    async def _run_resume_task(self, *, context: WebSocketBackgroundContext, task_run_id: str, approval_id: str, payload: dict[str, Any]) -> None:
        try:
            await context.websocket.app.state.orchestrator.resume(task_run_id=task_run_id, approval_id=approval_id, payload=payload)
        except Exception:
            logger.exception("taskRun.resume background 실행에 실패했습니다.")

    async def _run_cancel_task(self, *, context: WebSocketBackgroundContext, task_run_id: str) -> None:
        try:
            await context.websocket.app.state.orchestrator.cancel(task_run_id=task_run_id)
        except Exception:
            logger.exception("taskRun.cancel background 실행에 실패했습니다.")

    async def _send_result(self, context: WebSocketCommandContext, response_type: str, request_id: Any, payload: dict[str, Any]) -> None:
        await context.send_json(
            {
                "protocolVersion": 1,
                "type": response_type,
                "requestId": request_id,
                "serverTime": utc_now().isoformat(),
                "payload": _jsonable(payload),
            }
        )

    async def _send_error(
        self,
        context: WebSocketCommandContext,
        request_id: Any,
        code: str,
        message: str,
        *,
        retryable: bool = False,
    ) -> None:
        await context.send_json(
            {
                "protocolVersion": 1,
                "type": "command.error",
                "requestId": request_id,
                "serverTime": utc_now().isoformat(),
                "error": {
                    "code": code,
                    "message": message,
                    "retryable": retryable,
                },
            }
        )


def _event_frame(frame_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocolVersion": 1,
        "type": frame_type,
        "serverTime": utc_now().isoformat(),
        "payload": _jsonable(payload),
    }


def _create_public_session(context: WebSocketCommandContext, *, content: str, model: str | None) -> dict[str, Any]:
    session_id = new_id("session")
    context.websocket.app.state.session_store.create_session(
        session_id=session_id,
        session_key=session_id,
        source=_PUBLIC_SESSION_SOURCE,
        user_id=context.auth.user_id,
        model=model,
        title=_derive_session_title(content),
        metadata={"source": _PUBLIC_SESSION_SOURCE},
    )
    session = context.websocket.app.state.session_store.get_session(session_id)
    if session is None:
        raise WebSocketCommandError("internal_error", "session was not created", retryable=True)
    return session


def _create_task_transcript_session(session_store: Any, *, session_id: str, owner_key: str, title: str | None, model: str | None) -> str:
    transcript_session_id = new_id("agent_session")
    session_store.create_session(
        session_id=transcript_session_id,
        session_key=session_id,
        source=_TASK_TRANSCRIPT_SOURCE,
        user_id=owner_key,
        model=model,
        parent_session_id=session_id,
        title=title,
        metadata={"source": _TASK_TRANSCRIPT_SOURCE, "public_session_id": session_id},
    )
    return transcript_session_id


def _get_public_session(context: WebSocketCommandContext, session_id: str) -> dict[str, Any]:
    session = context.websocket.app.state.session_store.get_session(session_id)
    if session is None or not _is_public_session(session):
        raise WebSocketCommandError("not_found", "session not found")
    return session


def _is_public_session(session: dict[str, Any]) -> bool:
    metadata = dict(session.get("metadata") or {})
    return session.get("source") == _PUBLIC_SESSION_SOURCE or metadata.get("source") == _PUBLIC_SESSION_SOURCE


def _public_session_payload(session: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": str(session["id"]),
        "session_key": session.get("session_key"),
        "title": session.get("title"),
        "owner_key": session.get("user_id"),
        "status": session.get("status"),
        "source": session.get("source"),
        "parent_session_id": session.get("parent_session_id"),
        "message_count": int(session.get("message_count") or 0),
        "metadata": dict(session.get("metadata") or {}),
        "created_at": session.get("created_at") or session.get("started_at"),
        "updated_at": session.get("updated_at"),
        "ended_at": session.get("ended_at"),
    }


def _message_payload(message: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(message.get("metadata") or {})
    return {
        "id": int(message["id"]),
        "session_id": str(message["session_id"]),
        "role": str(message["role"]),
        "content": message.get("content"),
        "task_run_id": metadata.get("task_run_id") or metadata.get("taskRunId"),
        "metadata": metadata,
        "timestamp": message.get("timestamp"),
        "finish_reason": message.get("finish_reason"),
    }


def _active_task_payload(task: Any, steps: list[Any], *, source: str, repository: Any) -> dict[str, Any]:
    current_step = _select_current_step(task, steps)
    return {
        "task_run_id": task.task_run_id,
        "source": source,
        "session_key": task.session_key,
        "status": task.status,
        "title": task.title,
        "current_step_run_id": task.current_step_run_id,
        "current_step": _jsonable(current_step) if current_step is not None else None,
        "updated_at": task.updated_at,
        "wait_reason": (task.wait_payload or {}).get("reason"),
        "pending_approval": _pending_approval_payload(repository.get_open_approval(task.task_run_id)),
    }


def _projection_steps(projection: Any, task_run_id: str) -> list[Any]:
    steps = []
    for step_run_id in projection.list_task_steps(task_run_id):
        step = projection.get_step_snapshot(step_run_id)
        if step is not None:
            steps.append(step)
    return steps


def _select_current_step(task: Any, steps: list[Any]) -> Any | None:
    if task.current_step_run_id:
        for step in steps:
            if step.step_run_id == task.current_step_run_id:
                return step
    active_statuses = {"PENDING", "RUNNING", "WAITING", "BLOCKED"}
    for step in steps:
        if step.status in active_statuses:
            return step
    return steps[-1] if steps else None


def _pending_approval_payload(approval: dict[str, Any] | None) -> dict[str, Any] | None:
    if approval is None:
        return None
    request_payload = dict(approval.get("request_payload") or {})
    return {
        "approval_id": approval.get("approval_id"),
        "step_run_id": approval.get("step_run_id"),
        "status": approval.get("status"),
        "reason": request_payload.get("reason") or request_payload.get("approvalReason"),
        "tool_call_id": request_payload.get("pending_tool_call_id") or request_payload.get("tool_call_id"),
        "tool_name": request_payload.get("pending_tool_name") or request_payload.get("tool_name"),
        "requested_at": approval.get("created_at") or approval.get("requested_at"),
        "can_approve": bool(approval.get("can_approve", approval.get("status") == "PENDING")),
        "can_reject": bool(approval.get("can_reject", approval.get("status") == "PENDING")),
    }


def _ensure_owner(context: WebSocketCommandContext, owner_key: Any) -> None:
    if str(owner_key or "") != str(context.auth.user_id):
        raise WebSocketCommandError("forbidden", "forbidden")


def _assistant_content_from_task(task: Any) -> str:
    result_payload = dict(getattr(task, "result_payload", {}) or {})
    for key in ("text", "output_text", "summary", "message", "content"):
        value = result_payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if getattr(task, "progress_summary", None):
        return str(task.progress_summary)
    if getattr(task, "error_message", None):
        return str(task.error_message)
    if getattr(task, "status", None) == "WAITING":
        return "추가 확인이 필요합니다."
    return "요청 처리가 완료되었습니다."


def _derive_session_title(content: str) -> str:
    title = " ".join(content.split())
    return title[:60] or "새 AI 대화"


def _required_str(payload: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    label = keys[0]
    raise WebSocketCommandError("invalid_payload", f"{label} is required")


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    raise WebSocketCommandError("invalid_payload", "expected string")


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise WebSocketCommandError("invalid_payload", "expected integer")
    try:
        result = int(value)
    except (TypeError, ValueError) as error:
        raise WebSocketCommandError("invalid_payload", "expected integer") from error
    if result < 0:
        raise WebSocketCommandError("invalid_payload", "expected non-negative integer")
    return result


def _positive_int(value: Any, *, default: int, maximum: int) -> int:
    result = default if value is None else _optional_int(value)
    if result is None or result < 1:
        raise WebSocketCommandError("invalid_payload", "expected positive integer")
    return min(result, maximum)


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=False)
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value
