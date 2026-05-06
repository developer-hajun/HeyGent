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
_SESSION_MESSAGES_LIST_RESULT_TYPE = "session.messages.list.result"
_TASK_RUNS_ACTIVE_LIST_RESULT_TYPE = "taskRuns.active.list.result"


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
    after_response_callbacks: list[Callable[[], None]]


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

        callback_start_index = len(context.after_response_callbacks)
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
        callbacks = context.after_response_callbacks[callback_start_index:]
        del context.after_response_callbacks[callback_start_index:]
        for callback in callbacks:
            callback()
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
                "items": [_public_session_payload(session, context=context) for session in selected],
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
            _SESSION_MESSAGES_LIST_RESULT_TYPE,
            {
                "session_id": session_id,
                "after_message_id": after_message_id,
                "limit": limit,
                "total_count": len(items),
                "next_after_message_id": items[-1]["id"] if items else None,
                "items": items,
                "messages": items,
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
        # 프로세스 메모리가 비어도 같은 clientMessageId로 이미 저장된 메시지가 있으면
        # 새 TaskRun을 만들지 않고 기존 accepted 응답을 재구성한다.
        durable_existing = _find_accepted_message_by_client_id(
            context,
            session_id=session_id,
            client_message_id=client_message_id,
        )
        if durable_existing is not None:
            self._accepted_messages[idempotency_key] = durable_existing
            return "session.message.accepted", dict(durable_existing)

        if session_id:
            session = _get_public_session(context, session_id)
            _ensure_owner(context, session.get("user_id"))
        else:
            session = _create_public_session(context, content=content, model=model)
            session_id = str(session["id"])

        session_store = context.websocket.app.state.session_store
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

        handler = context.websocket.app.state.tool_registry.resolve()
        task = context.websocket.app.state.task_engine.planner.materialize_task(
            owner_key=context.auth.user_id,
            session_key=session_id,
            input_payload=task_input,
            handler=handler,
        )
        context.websocket.app.state.repository.create_task(task)
        user_message_ref = session_store.append_message(
            session_id=session_id,
            role="user",
            content=content,
            metadata={
                "source": _PUBLIC_SESSION_SOURCE,
                # clientMessageId는 재전송/낙관적 UI 병합을 추적하기 위한 idempotency 키다.
                # accessToken과 달리 비밀값이 아니며, durable 저장되어도 보안 경계가 흔들리지 않는다.
                "client_message_id": client_message_id,
                "task_run_id": task.task_run_id,
            },
        )
        context.session_service.subscribe_task(
            session_id=context.gateway_session_id,
            websocket=context.websocket,
            task_run_id=task.task_run_id,
        )

        accepted = {
            "session_id": session_id,
            "user_message_id": _stored_message_id(session_store, session_id=session_id, stored_ref=user_message_ref),
            "assistant_message_id": None,
            "task_run_id": task.task_run_id,
            "status": task.status,
            "client_message_id": client_message_id,
        }
        self._accepted_messages[idempotency_key] = accepted

        def start_background_task() -> None:
            background_context = WebSocketBackgroundContext(websocket=context.websocket, send_json=context.send_json)
            background_task = asyncio.create_task(
                self._run_created_message_task(
                    context=background_context,
                    session_id=session_id,
                    user_message_id=user_message_ref,
                    task=task,
                    handler=handler,
                )
            )
            context.background_tasks.add(background_task)
            background_task.add_done_callback(context.background_tasks.discard)

        # accepted frame을 먼저 보낸 뒤 agent.loop/task.event fan-out을 시작한다.
        context.after_response_callbacks.append(start_background_task)
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
        items = list(items_by_task_run_id.values())
        return (
            _TASK_RUNS_ACTIVE_LIST_RESULT_TYPE,
            {
                "session_id": session_id,
                "items": items,
                "task_runs": items,
                "total_count": len(items),
            },
        )

    async def _task_run_snapshot_get(self, payload: dict[str, Any], context: WebSocketCommandContext) -> tuple[str, dict[str, Any]]:
        task_run_id = _required_str(payload, "taskRunId", "task_run_id")
        include_steps = bool(payload.get("includeSteps", payload.get("include_steps", True)))
        include_flow = bool(payload.get("includeFlow", payload.get("include_flow", False)))
        include_events = bool(payload.get("includeEvents", payload.get("include_events", True)))
        repository = context.websocket.app.state.repository
        task = repository.get_task(task_run_id)
        if task is None:
            raise WebSocketCommandError("not_found", "task not found")
        _ensure_owner(context, task.owner_key)
        steps = repository.list_steps(task_run_id) if include_steps or include_flow else []
        pending_approval = _pending_approval_payload(repository.get_open_approval(task_run_id))
        events = (
            _task_events_payload(
                repository=repository,
                projection=getattr(context.websocket.app.state, "task_projection_store", None),
                task_run_id=task_run_id,
            )
            if include_events
            else []
        )
        snapshot = {
            "task": _jsonable(task),
            "task_run": _jsonable(task),
            "pending_approval": pending_approval,
            "approvals": [pending_approval] if pending_approval is not None else [],
            "events": events,
        }
        if include_steps:
            step_payloads = [_jsonable(step) for step in steps]
            snapshot["steps"] = step_payloads
            snapshot["step_runs"] = step_payloads
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
            # Redis projection은 빠르지만 최근 구간만 보관한다.
            # afterSequence보다 앞 구간이 잘렸으면 durable event 저장소로 fallback해야 한다.
            events = projection.list_recent_events(task_run_id)
            if after_sequence is not None:
                events = [event for event in events if int(event.get("sequence") or 0) > after_sequence]
            events = events[:limit]
            if after_sequence is not None:
                latest_sequence = projection.get_latest_sequence(task_run_id)
                min_returned_sequence = min((int(event.get("sequence") or 0) for event in events), default=None)
                retention_exceeded = bool(
                    latest_sequence is not None
                    and latest_sequence > after_sequence
                    and (not events or (min_returned_sequence is not None and min_returned_sequence > after_sequence + 1))
                )

        if not events or retention_exceeded:
            # projection에서 못 찾은 구간은 DB에 저장된 canonical event로 복구한다.
            stored_events = repository.list_events(task_run_id)
            if after_sequence is not None:
                stored_events = [event for event in stored_events if int(event.sequence or 0) > after_sequence]
            durable_events = [_jsonable(event) for event in stored_events[:limit]]
            if durable_events:
                events = durable_events

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
        resume_payload = _normalize_resume_payload(resume_payload)
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
            assistant_message_ref = context.websocket.app.state.session_store.append_message(
                session_id=session_id,
                role="assistant",
                content=content,
                metadata={
                    "source": _PUBLIC_SESSION_SOURCE,
                    "task_run_id": completed_task.task_run_id,
                    "status": completed_task.status,
                    "user_message_id": str(user_message_id),
                },
                finish_reason="stop" if completed_task.status in _TERMINAL_TASK_STATUSES else None,
            )
            # 현재 Task Engine에는 토큰 단위 streaming hook이 없으므로 delta를 합성하지 않는다.
            # 프론트에는 durable assistant 메시지가 저장된 뒤 completed frame만 보낸다.
            await context.send_json(
                _event_frame(
                    "session.message.completed",
                    {
                        "session_id": session_id,
                        "message_id": _stored_message_id(
                            context.websocket.app.state.session_store,
                            session_id=session_id,
                            stored_ref=assistant_message_ref,
                        ),
                        "content": content,
                        "task_run_id": completed_task.task_run_id,
                        "status": completed_task.status,
                        "finish_reason": "stop" if completed_task.status in _TERMINAL_TASK_STATUSES else None,
                    },
                )
            )
        except Exception:
            logger.exception("session.message.create background 실행에 실패했습니다.")
            # accepted 이후 background 실행이 실패해도 client가 placeholder를 무기한 기다리면 안 된다.
            # 실패 frame은 durable TaskRun event와 별개로 현재 대화 UI의 pending assistant 상태를 닫는 역할을 한다.
            try:
                await context.send_json(
                    _event_frame(
                        "session.message.failed",
                        {
                            "session_id": session_id,
                            "message_id": f"failed:{task.task_run_id}",
                            "user_message_id": str(user_message_id),
                            "task_run_id": task.task_run_id,
                            "status": "FAILED",
                            "error": {
                                "code": "background_task_failed",
                                "message": "AI 응답 생성 중 오류가 발생했습니다.",
                                "retryable": True,
                            },
                        },
                    )
                )
            except Exception:
                logger.exception("session.message.failed frame 전송에 실패했습니다.")

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


def _public_session_payload(session: dict[str, Any], *, context: WebSocketCommandContext | None = None) -> dict[str, Any]:
    payload = {
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
    if context is not None:
        payload.update(_session_list_preview_payload(context, session_id=str(session["id"])))
    return payload


def _session_list_preview_payload(context: WebSocketCommandContext, *, session_id: str) -> dict[str, Any]:
    """세션 목록만으로 사이드바를 복구할 수 있게 최근 메시지와 TaskRun 상태를 붙인다.

    상세 화면은 별도 messages/snapshot query를 다시 호출하지만, 목록은 이 값만으로
    mock preview나 임의 spinner 없이 실제 DB 상태를 표시한다.
    """

    result: dict[str, Any] = {
        "last_message": None,
        "last_message_at": None,
        "active_task_run_id": None,
        "last_task_run_status": None,
    }

    messages = context.websocket.app.state.session_store.list_messages(session_id)
    if messages:
        last_message = messages[-1]
        result["last_message"] = last_message.get("content")
        result["last_message_at"] = last_message.get("timestamp")

    tasks = context.websocket.app.state.repository.list_tasks(session_key=session_id, limit=50, offset=0)
    if not tasks:
        return result

    active_task = next((task for task in tasks if task.status in _ACTIVE_TASK_STATUSES), None)
    latest_task = active_task or tasks[0]
    result["last_task_run_status"] = latest_task.status
    if active_task is not None:
        result["active_task_run_id"] = active_task.task_run_id
    return result


def _message_payload(message: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(message.get("metadata") or {})
    sequence = int(message["id"])
    durable_message_id = message.get("message_id") or message.get("messageId") or sequence
    return {
        "id": sequence,
        "message_id": str(durable_message_id),
        "message_sequence": sequence,
        "session_id": str(message["session_id"]),
        "role": str(message["role"]),
        "content": message.get("content"),
        "task_run_id": metadata.get("task_run_id") or metadata.get("taskRunId"),
        "client_message_id": metadata.get("client_message_id") or metadata.get("clientMessageId"),
        "metadata": metadata,
        "timestamp": message.get("timestamp"),
        "created_at": message.get("timestamp"),
        "finish_reason": message.get("finish_reason"),
    }


def _stored_message_id(session_store: Any, *, session_id: str, stored_ref: Any) -> str:
    """append_message 반환값을 WebSocket용 durable message_id로 정규화한다.

    Postgres 저장소는 HTTP 증분 조회 호환성을 위해 append_message에서 세션 내 sequence를
    돌려줄 수 있다. WebSocket 채팅 store의 최종 key는 DB message_id가 기준이므로,
    저장 직후 row를 다시 읽어 실제 message_id가 있으면 그 값을 우선 사용한다.
    """

    stored_ref_text = str(stored_ref)
    for message in session_store.list_messages(session_id):
        message_payload = _message_payload(message)
        if str(message_payload["id"]) == stored_ref_text or str(message_payload["message_id"]) == stored_ref_text:
            return str(message_payload["message_id"])
    return stored_ref_text


def _find_accepted_message_by_client_id(
    context: WebSocketCommandContext,
    *,
    session_id: str | None,
    client_message_id: str,
) -> dict[str, Any] | None:
    """durable 저장소에서 clientMessageId 재전송 여부를 찾는다."""

    session_store = context.websocket.app.state.session_store
    candidate_sessions = [session_store.get_session(session_id)] if session_id else session_store.list_sessions(user_id=context.auth.user_id, limit=10_000, offset=0)
    for session in candidate_sessions:
        if session is None or not _is_public_session(session):
            continue
        if str(session.get("user_id") or "") != str(context.auth.user_id):
            continue
        public_session_id = str(session["id"])
        for message in session_store.list_messages(public_session_id):
            metadata = dict(message.get("metadata") or {})
            if metadata.get("client_message_id") != client_message_id and metadata.get("clientMessageId") != client_message_id:
                continue
            task_run_id = metadata.get("task_run_id") or metadata.get("taskRunId")
            if not task_run_id:
                continue
            return {
                "session_id": public_session_id,
                "user_message_id": str(_message_payload(message)["message_id"]),
                "assistant_message_id": _find_assistant_message_id_for_task(session_store, public_session_id, str(task_run_id)),
                "task_run_id": str(task_run_id),
                "status": _task_status_for_payload(context, str(task_run_id)),
                "client_message_id": client_message_id,
            }
    return None


def _find_assistant_message_id_for_task(session_store: Any, session_id: str, task_run_id: str) -> str | None:
    for message in session_store.list_messages(session_id):
        if str(message.get("role") or "") != "assistant":
            continue
        metadata = dict(message.get("metadata") or {})
        if str(metadata.get("task_run_id") or metadata.get("taskRunId") or "") == task_run_id:
            return str(_message_payload(message)["message_id"])
    return None


def _task_status_for_payload(context: WebSocketCommandContext, task_run_id: str) -> str | None:
    task = context.websocket.app.state.repository.get_task(task_run_id)
    return str(task.status) if task is not None else None


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


def _task_events_payload(
    *,
    repository: Any,
    projection: Any,
    task_run_id: str,
    limit: int = 200,
) -> list[dict[str, Any]]:
    if projection is not None:
        events = projection.list_recent_events(task_run_id)
        if events:
            return [_jsonable(event) for event in events[:limit]]
    return [_jsonable(event) for event in repository.list_events(task_run_id)[:limit]]


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
        "task_run_id": approval.get("task_run_id"),
        "step_run_id": approval.get("step_run_id"),
        "status": approval.get("status"),
        "reason": request_payload.get("reason") or request_payload.get("approvalReason"),
        "tool_call_id": request_payload.get("pending_tool_call_id") or request_payload.get("tool_call_id"),
        "tool_name": request_payload.get("pending_tool_name") or request_payload.get("tool_name"),
        "payload": request_payload,
        "request_payload": request_payload,
        "requested_at": approval.get("created_at") or approval.get("requested_at"),
        "created_at": approval.get("created_at") or approval.get("requested_at"),
        "can_approve": bool(approval.get("can_approve", approval.get("status") == "PENDING")),
        "can_reject": bool(approval.get("can_reject", approval.get("status") == "PENDING")),
    }


def _normalize_resume_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """프론트 승인 command shape를 agent.loop resume shape로 맞춘다.

    UI는 디버깅을 위해 decision/response를 함께 보내지만, 실제 tool resume 로직은
    top-level approved/reason/message 값을 읽는다. 서버 경계에서 한 번만 펴서 저장/실행한다.
    """

    normalized = dict(payload)
    response = normalized.get("response")
    if isinstance(response, dict):
        normalized.update(response)

    decision = str(normalized.get("decision") or "").strip().upper()
    if "approved" not in normalized and decision:
        normalized["approved"] = decision in {"APPROVED", "APPROVE", "ACCEPTED", "YES"}
    if normalized.get("approved") is False and not normalized.get("reason"):
        normalized["reason"] = normalized.get("message") or "사용자가 도구 실행을 거절했습니다"
    return normalized


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
