from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.api.session_agent_profiles import (
    agent_profile_prompt_payload as _agent_profile_prompt_payload,
    profile_model as _profile_model,
    profile_provider_name as _profile_provider_name,
)
from app.api.ws.command_types import (
    WebSocketAuthContext,
    WebSocketBackgroundContext,
    WebSocketCommandContext,
    WebSocketCommandError,
)
from app.api.memory_context import attach_persistent_memory_context
from app.api.memory_mark_used import mark_used_recalled_memories
from app.api.memory_observation import attach_memory_observation_to_task
from app.api.memory_writeback import writeback_persistent_memory_candidates
from app.contracts.task.task_status import TaskStatus
from app.core.time import utc_now
from app.core.utils.ids import new_id
from app.domain.orchestration.capabilities import apply_task_capabilities
from app.domain.orchestration.contracts import OrchestrationRequest
from app.domain.orchestration.run_lifecycle import classify_task_run_liveness
from app.domain.session.conversation_history import build_conversation_history
from app.domain.session.history_compaction import compact_conversation_history
from app.domain.session.session_runtime_state import get_system_prompt_snapshot
from app.domain.tasks.activity_transcript import build_activity_transcript
from app.domain.tasks.display_context import build_task_display_context
from app.domain.work import WorkService

# ── 헬퍼 모듈 ──────────────────────────────────────────────────────────
from app.api.ws.command_handlers.constants import (
    ACTIVE_TASK_STATUSES as _ACTIVE_TASK_STATUSES,
    TERMINAL_TASK_STATUSES as _TERMINAL_TASK_STATUSES,
    PUBLIC_SESSION_SOURCE as _PUBLIC_SESSION_SOURCE,
    TASK_TRANSCRIPT_SOURCE as _TASK_TRANSCRIPT_SOURCE,
    ACTIVE_DIRECT_RUN_TTL_SECONDS as _ACTIVE_DIRECT_RUN_TTL_SECONDS,
    PROTECTED_SESSION_METADATA_KEYS as _PROTECTED_SESSION_METADATA_KEYS,
    SESSION_METADATA_PATCH_ALLOWLIST as _SESSION_METADATA_PATCH_ALLOWLIST,
    SESSION_SETTINGS_ALLOWLIST as _SESSION_SETTINGS_ALLOWLIST,
    PUBLIC_SESSION_TOOLSETS as _PUBLIC_SESSION_TOOLSETS,
    OPENAI_MODEL_FALLBACKS as _OPENAI_MODEL_FALLBACKS,
)
from app.api.ws.command_handlers.session_helpers import (
    create_public_session as _create_public_session,
    create_task_transcript_session as _create_task_transcript_session,
    default_agent_loop_toolsets as _default_agent_loop_toolsets,
    derive_session_title as _derive_session_title,
    ensure_owner as _ensure_owner,
    ensure_session_idle as _ensure_session_idle,
    find_accepted_message_by_client_id as _find_accepted_message_by_client_id,
    find_assistant_message_id_for_task as _find_assistant_message_id_for_task,
    get_public_session as _get_public_session,
    is_active_direct_run_stale as _is_active_direct_run_stale,
    is_expired_running_task as _is_expired_running_task,
    is_live_active_task as _is_live_active_task,
    is_public_session as _is_public_session,
    is_sidebar_active_task as _is_sidebar_active_task,
    json_dumps as _json_dumps,
    json_load as _json_load,
    jsonable as _jsonable,
    list_openai_models_for_user as _list_openai_models_for_user,
    message_payload as _message_payload,
    normalize_session_settings as _normalize_session_settings,
    optional_int as _optional_int,
    optional_str as _optional_str,
    owner_filter as _owner_filter,
    owner_user_id as _owner_user_id,
    patch_public_session_metadata as _patch_public_session_metadata,
    positive_int as _positive_int,
    prepare_retry_turn as _prepare_retry_turn,
    public_session_payload as _public_session_payload,
    recover_stale_task_if_needed as _recover_stale_task_if_needed,
    refresh_stale_running_guard as _refresh_stale_running_guard,
    required_str as _required_str,
    session_command_signature as _session_command_signature,
    session_settings_snapshot as _session_settings_snapshot,
    apply_session_settings_snapshot as _apply_session_settings_snapshot,
    stored_message_id as _stored_message_id,
    task_status_for_payload as _task_status_for_payload,
    truncate_public_session_tail as _truncate_public_session_tail,
    update_public_session_title as _update_public_session_title,
    validate_metadata_patch as _validate_metadata_patch,
    assistant_content_from_task as _assistant_content_from_task,
)
from app.api.ws.command_handlers.task_helpers import (
    active_task_payload as _active_task_payload,
    apply_work_execution_defaults as _apply_work_execution_defaults,
    apply_ws_linked_work_result as _apply_ws_linked_work_result,
    attach_effective_skill_names as _attach_effective_skill_names,
    attach_main_agent_context as _attach_main_agent_context,
    attach_session_agent_candidates as _attach_session_agent_candidates,
    attach_target_agent_context as _attach_target_agent_context,
    attach_work_context_or_ws_error as _attach_work_context_or_ws_error,
    event_frame as _event_frame,
    mark_ws_linked_work_run_failed as _mark_ws_linked_work_run_failed,
    normalize_resume_payload as _normalize_resume_payload,
    pending_approval_payload as _pending_approval_payload,
    projection_steps as _projection_steps,
    seed_default_session_agents_if_requested as _seed_default_session_agents_if_requested,
    select_current_step as _select_current_step,
    step_payload_with_display_context as _step_payload_with_display_context,
    task_events_payload as _task_events_payload,
    task_snapshot_payload as _task_snapshot_payload,
    work_id_from_task_input as _work_id_from_task_input,
)

logger = logging.getLogger(__name__)

_SESSION_MESSAGES_LIST_RESULT_TYPE = "session.messages.list.result"
_TASK_RUNS_ACTIVE_LIST_RESULT_TYPE = "taskRuns.active.list.result"


class WebSocketCommandRouter:
    """인증 이후 WebSocket command/query를 처리한다.

    기존 gateway는 auth.start/auth.ok/subscribe.task/ping을 담당하고,
    이 라우터는 requestId가 있는 command/query 응답을 같은 연결로 되돌린다.
    """

    def __init__(self) -> None:
        self._accepted_messages: dict[tuple[str, str, str], dict[str, Any]] = {}
        self._accepted_resumes: dict[tuple[str, str], dict[str, Any]] = {}
        self._accepted_cancels: dict[tuple[str, str], dict[str, Any]] = {}
        self._accepted_session_commands: dict[tuple[str, str, str], tuple[str, str, dict[str, Any]]] = {}

    async def handle(self, message: dict[str, Any], context: WebSocketCommandContext) -> bool:
        message_type = message.get("type")
        if not isinstance(message_type, str):
            return False

        handlers = {
            "session.list": self._session_list,
            "session.messages.list": self._session_messages_list,
            "session.message.create": self._session_message_create,
            "session.message.retry": self._session_message_retry,
            "session.message.undo": self._session_message_undo,
            "session.history.compact": self._session_history_compact,
            "session.update": self._session_update,
            "session.archive": self._session_archive,
            "session.delete": self._session_delete,
            "session.settings.update": self._session_settings_update,
            "model.options": self._model_options,
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

    def _replay_session_command(
        self,
        context: WebSocketCommandContext,
        *,
        session_id: str,
        command_id: str,
        signature: str,
    ) -> tuple[str, dict[str, Any]] | None:
        key = (context.auth.user_id, session_id, command_id)
        session_store = context.websocket.app.state.session_store
        if hasattr(session_store, "get_session_command_receipt"):
            receipt = session_store.get_session_command_receipt(
                owner_key=context.auth.user_id,
                session_id=session_id,
                client_command_id=command_id,
            )
            if receipt is not None:
                if receipt.get("command_signature") != signature:
                    raise WebSocketCommandError("conflict", "clientCommandId was already used with a different payload")
                response_payload = dict(receipt.get("response_payload") or {})
                response_type = str(response_payload.pop("_response_type"))
                return response_type, response_payload
        existing = self._accepted_session_commands.get(key)
        if existing is None:
            return None
        existing_signature, response_type, response_payload = existing
        if existing_signature != signature:
            raise WebSocketCommandError("conflict", "clientCommandId was already used with a different payload")
        return response_type, dict(response_payload)

    def _remember_session_command(
        self,
        context: WebSocketCommandContext,
        *,
        session_id: str,
        command_id: str,
        signature: str,
        response: tuple[str, dict[str, Any]],
    ) -> None:
        response_type, response_payload = response
        session_store = context.websocket.app.state.session_store
        durable_payload = {"_response_type": response_type, **_jsonable(response_payload)}
        if hasattr(session_store, "remember_session_command_receipt"):
            session_store.remember_session_command_receipt(
                owner_key=context.auth.user_id,
                session_id=session_id,
                client_command_id=command_id,
                command_signature=signature,
                response_payload=durable_payload,
            )
        self._accepted_session_commands[(context.auth.user_id, session_id, command_id)] = (
            signature,
            response_type,
            _jsonable(response_payload),
        )

    async def _session_list(self, payload: dict[str, Any], context: WebSocketCommandContext) -> tuple[str, dict[str, Any]]:
        page = _positive_int(payload.get("page"), default=1, maximum=10_000)
        page_size = _positive_int(payload.get("pageSize", payload.get("page_size")), default=20, maximum=50)
        include_archived = bool(payload.get("includeArchived", payload.get("include_archived", False)))
        offset = (page - 1) * page_size
        session_store = context.websocket.app.state.session_store
        sessions = session_store.list_sessions(
            user_id=context.auth.user_id,
            limit=page_size,
            offset=offset,
            include_archived=include_archived,
            source=_PUBLIC_SESSION_SOURCE,
        )
        selected = [session for session in sessions if _is_public_session(session)]
        total_count = (
            session_store.count_sessions(
                user_id=context.auth.user_id,
                include_archived=include_archived,
                source=_PUBLIC_SESSION_SOURCE,
            )
            if hasattr(session_store, "count_sessions")
            else offset + len(selected)
        )
        return (
            "session.list.result",
            {
                "items": [_public_session_payload(session, context=context) for session in selected],
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "has_previous": page > 1,
                "has_next": offset + len(selected) < total_count,
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
        initial_settings_payload = payload.get("settings")
        if initial_settings_payload is not None and not isinstance(initial_settings_payload, dict):
            raise WebSocketCommandError("invalid_payload", "settings must be an object")
        initial_settings = _normalize_session_settings(initial_settings_payload) if isinstance(initial_settings_payload, dict) else {}

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
            if initial_settings:
                raise WebSocketCommandError("invalid_payload", "settings can only be used when creating a new session")
            session = _get_public_session(context, session_id)
            _ensure_owner(context, session.get("user_id"))
            session = _refresh_stale_running_guard(context, session)
            _ensure_session_idle(session)
        else:
            session = _create_public_session(context, content=content, model=model, settings=initial_settings)
            session_id = str(session["id"])

        session_store = context.websocket.app.state.session_store
        base_history_version = int(session.get("history_version") or 0)
        conversation_history = compact_conversation_history(
            build_conversation_history(session_store.list_messages(session_id))
        )
        task_input = dict(input_payload)
        task_input["sessionId"] = session_id
        task_input["ownerKey"] = context.auth.user_id
        task_input["ownerUserId"] = _owner_user_id(context.auth.user_id)
        settings_snapshot = _session_settings_snapshot(session)
        _seed_default_session_agents_if_requested(
            context.websocket.app.state,
            task_input=task_input,
            session_id=session_id,
            owner_key=context.auth.user_id,
        )
        main_profile = _attach_main_agent_context(
            context.websocket.app.state,
            task_input=task_input,
            session_id=session_id,
            owner_key=context.auth.user_id,
        )
        session_agent_profiles = _attach_session_agent_candidates(
            context.websocket.app.state,
            task_input=task_input,
            session_id=session_id,
            owner_key=context.auth.user_id,
        )
        if session_agent_profiles:
            task_input["allowSessionAgentRootWork"] = True
        profile_model = _profile_model(main_profile) if main_profile is not None else None
        effective_model = str(profile_model or settings_snapshot.get("model") or model or "").strip() or None
        if effective_model:
            task_input["model"] = effective_model
        profile_provider = _profile_provider_name(main_profile) if main_profile is not None else None
        if profile_provider:
            task_input["provider_name"] = profile_provider
        transcript_session_id = _create_task_transcript_session(
            session_store,
            session_id=session_id,
            owner_key=context.auth.user_id,
            title=session.get("title") or content[:120],
            model=effective_model,
        )
        task_input["prompt"] = content
        task_input["transcript_session_id"] = transcript_session_id
        task_input["conversation_history"] = conversation_history
        task_input["system_prompt_snapshot"] = get_system_prompt_snapshot(session)
        task_input["base_history_version"] = base_history_version
        _apply_session_settings_snapshot(task_input, settings_snapshot, session=session)
        work_id = _work_id_from_task_input(task_input)
        work_metadata: dict[str, Any] = {}
        if work_id is not None:
            work = _attach_work_context_or_ws_error(
                context,
                task_input=task_input,
                work_id=work_id,
                session_id=session_id,
                owner_key=context.auth.user_id,
            )
            work_metadata = {
                "work_id": work.work_id,
                "work_identifier": work.identifier,
                "work_title": work.title,
                "work_assignee_agent_id": work.assignee_agent_id,
            }
        apply_task_capabilities(
            task_input,
            skill_registry=getattr(context.websocket.app.state, "skill_registry", None),
            default_toolsets=_default_agent_loop_toolsets(context.websocket.app.state),
        )
        # token memory context는 durable payload에 넣지 않는다. backend 호출이 필요해지면
        # context.auth.access_token에서만 꺼내 쓰도록 경계를 고정한다.
        await attach_persistent_memory_context(
            app_state=context.websocket.app.state,
            task_input=task_input,
            user_id=str(context.auth.user_id),
            query=content,
            workspace_key=context.auth.workspace_key or session.get("workspace_key"),
        )

        handler = context.websocket.app.state.tool_registry.resolve()
        task = context.websocket.app.state.task_engine.planner.materialize_task(
            owner_key=context.auth.user_id,
            session_key=session_id,
            input_payload=task_input,
            handler=handler,
        )
        user_append = session_store.append_user_message_and_start_task(
            owner_key=context.auth.user_id,
            session_id=session_id,
            content=content,
            client_message_id=client_message_id,
            task_run_id=task.task_run_id,
            base_history_version=base_history_version,
            metadata_patch=work_metadata,
        )
        if user_append.get("duplicate"):
            accepted = {
                "session_id": session_id,
                "user_message_id": _stored_message_id(session_store, session_id=session_id, stored_ref=user_append["message_id"]),
                "assistant_message_id": _find_assistant_message_id_for_task(session_store, session_id, str(user_append["task_run_id"])),
                "task_run_id": str(user_append["task_run_id"]),
                "status": _task_status_for_payload(context, str(user_append["task_run_id"])),
                "client_message_id": client_message_id,
                "history_version": user_append["after_user_message_version"],
            }
            self._accepted_messages[idempotency_key] = accepted
            return "session.message.accepted", dict(accepted)
        task.input_payload = {
            **dict(task.input_payload or {}),
            "after_user_message_version": user_append["after_user_message_version"],
            "completion_expected_version": user_append["completion_expected_version"],
            "prompt_message_id": str(user_append["message_id"]),
            "promptMessageId": str(user_append["message_id"]),
        }
        task_execution_supervisor = getattr(context.websocket.app.state, "task_execution_supervisor", None)
        try:
            if task_execution_supervisor is not None:
                background_context = WebSocketBackgroundContext(websocket=context.websocket, send_json=context.send_json)

                async def finish_supervised_task(completed_task: Any) -> None:
                    await self._finish_created_message_task(
                        context=background_context,
                        session_id=session_id,
                        user_message_id=int(user_append["message_id"]),
                        task=task,
                        completed_task=completed_task,
                    )

                task = await task_execution_supervisor.submit(
                    OrchestrationRequest(
                        task_run_id=task.task_run_id,
                        owner_key=context.auth.user_id,
                        session_key=session_id,
                        input_payload=dict(task.input_payload or {}),
                    ),
                    on_complete=finish_supervised_task,
                )
            else:
                context.websocket.app.state.repository.create_direct_task(task)
            if work_id is not None:
                WorkService(context.websocket.app.state.work_repository).mark_run_started(
                    work_id=work_id,
                    task_run_id=task.task_run_id,
                )
        except Exception:
            session_store.clear_stale_running_task(
                owner_key=context.auth.user_id,
                session_id=session_id,
                task_run_id=task.task_run_id,
            )
            raise
        context.session_service.subscribe_task(
            session_id=context.gateway_session_id,
            websocket=context.websocket,
            task_run_id=task.task_run_id,
        )

        accepted = {
            "session_id": session_id,
            "user_message_id": _stored_message_id(session_store, session_id=session_id, stored_ref=user_append["message_id"]),
            "assistant_message_id": None,
            "task_run_id": task.task_run_id,
            "status": task.status,
            "client_message_id": client_message_id,
            "history_version": user_append["after_user_message_version"],
        }
        self._accepted_messages[idempotency_key] = accepted

        if task_execution_supervisor is None:
            def start_background_task() -> None:
                background_context = WebSocketBackgroundContext(websocket=context.websocket, send_json=context.send_json)
                background_task = asyncio.create_task(
                    self._run_created_message_task(
                        context=background_context,
                        session_id=session_id,
                        user_message_id=int(user_append["message_id"]),
                        task=task,
                        handler=handler,
                    )
                )
                context.background_tasks.add(background_task)
                background_task.add_done_callback(context.background_tasks.discard)

            # accepted frame을 먼저 보낸 뒤 agent.loop/task.event fan-out을 시작한다.
            context.after_response_callbacks.append(start_background_task)
        return "session.message.accepted", dict(accepted)

    async def _session_message_retry(self, payload: dict[str, Any], context: WebSocketCommandContext) -> tuple[str, dict[str, Any]]:
        session_id = _required_str(payload, "sessionId", "session_id")
        command_id = _required_str(payload, "clientCommandId", "client_command_id")
        target_message_id = _optional_str(payload.get("targetMessageId", payload.get("target_message_id")))
        model = _optional_str(payload.get("model"))
        session = _get_public_session(context, session_id)
        _ensure_owner(context, session.get("user_id"))
        session = _refresh_stale_running_guard(context, session)
        _ensure_session_idle(session)

        session_store = context.websocket.app.state.session_store
        retry_state = _prepare_retry_turn(
            session_store,
            owner_key=context.auth.user_id,
            session_id=session_id,
            target_message_id=target_message_id,
        )
        content = retry_state["content"]
        conversation_history = compact_conversation_history(build_conversation_history(retry_state["history_rows"]))
        try:
            settings_snapshot = _session_settings_snapshot(session)
            effective_model = str(settings_snapshot.get("model") or model or "").strip() or None
            transcript_session_id = _create_task_transcript_session(
                session_store,
                session_id=session_id,
                owner_key=context.auth.user_id,
                title=session.get("title") or str(content)[:120],
                model=effective_model,
            )
            task_input = {
                "prompt": content,
                "transcript_session_id": transcript_session_id,
                "conversation_history": conversation_history,
                "system_prompt_snapshot": get_system_prompt_snapshot(session),
                "base_history_version": retry_state["base_history_version"],
                "after_user_message_version": retry_state["completion_expected_version"],
                "completion_expected_version": retry_state["completion_expected_version"],
                "retry_source_message_id": retry_state["user_message_id"],
                "prompt_message_id": str(retry_state["user_message_id"]),
                "promptMessageId": str(retry_state["user_message_id"]),
                "client_command_id": command_id,
            }
            if effective_model:
                task_input["model"] = effective_model
            _apply_session_settings_snapshot(task_input, settings_snapshot, session=session)
            await attach_persistent_memory_context(
                app_state=context.websocket.app.state,
                task_input=task_input,
                user_id=str(context.auth.user_id),
                query=str(content),
                workspace_key=context.auth.workspace_key or session.get("workspace_key"),
            )
            handler = context.websocket.app.state.tool_registry.resolve()
            task = context.websocket.app.state.task_engine.planner.materialize_task(
                owner_key=context.auth.user_id,
                session_key=session_id,
                input_payload=task_input,
                handler=handler,
                task_run_id=retry_state["task_run_id"],
            )
            task_execution_supervisor = getattr(context.websocket.app.state, "task_execution_supervisor", None)
            if task_execution_supervisor is not None:
                background_context = WebSocketBackgroundContext(websocket=context.websocket, send_json=context.send_json)

                async def finish_supervised_retry(completed_task: Any) -> None:
                    await self._finish_created_message_task(
                        context=background_context,
                        session_id=session_id,
                        user_message_id=int(retry_state["user_message_id"]),
                        task=task,
                        completed_task=completed_task,
                    )

                task = await task_execution_supervisor.submit(
                    OrchestrationRequest(
                        task_run_id=task.task_run_id,
                        owner_key=context.auth.user_id,
                        session_key=session_id,
                        input_payload=dict(task.input_payload or {}),
                    ),
                    on_complete=finish_supervised_retry,
                )
            else:
                context.websocket.app.state.repository.create_direct_task(task)
            context.session_service.subscribe_task(
                session_id=context.gateway_session_id,
                websocket=context.websocket,
                task_run_id=task.task_run_id,
            )
        except Exception:
            session_store.clear_stale_running_task(
                owner_key=context.auth.user_id,
                session_id=session_id,
                task_run_id=str(retry_state["task_run_id"]),
            )
            raise
        accepted = {
            "session_id": session_id,
            "user_message_id": str(retry_state["user_message_id"]),
            "assistant_message_id": None,
            "task_run_id": task.task_run_id,
            "status": task.status,
            "client_command_id": command_id,
            "history_version": retry_state["completion_expected_version"],
        }

        if task_execution_supervisor is None:
            def start_background_task() -> None:
                background_context = WebSocketBackgroundContext(websocket=context.websocket, send_json=context.send_json)
                background_task = asyncio.create_task(
                    self._run_created_message_task(
                        context=background_context,
                        session_id=session_id,
                        user_message_id=int(retry_state["user_message_id"]),
                        task=task,
                        handler=handler,
                    )
                )
                context.background_tasks.add(background_task)
                background_task.add_done_callback(context.background_tasks.discard)

            context.after_response_callbacks.append(start_background_task)
        return "session.message.accepted", accepted

    async def _session_message_undo(self, payload: dict[str, Any], context: WebSocketCommandContext) -> tuple[str, dict[str, Any]]:
        session_id = _required_str(payload, "sessionId", "session_id")
        command_id = _required_str(payload, "clientCommandId", "client_command_id")
        until_message_id = _optional_str(payload.get("untilMessageId", payload.get("until_message_id")))
        session = _get_public_session(context, session_id)
        _ensure_owner(context, session.get("user_id"))
        session = _refresh_stale_running_guard(context, session)
        _ensure_session_idle(session)
        result = _truncate_public_session_tail(
            context.websocket.app.state.session_store,
            owner_key=context.auth.user_id,
            session_id=session_id,
            keep_through_message_id=until_message_id,
            default_remove_last=True,
        )
        return (
            "session.updated",
            {
                "session_id": session_id,
                "client_command_id": command_id,
                "history_version": result["history_version"],
                "messages": [_message_payload(message) for message in context.websocket.app.state.session_store.list_messages(session_id)],
            },
        )

    async def _session_history_compact(self, payload: dict[str, Any], context: WebSocketCommandContext) -> tuple[str, dict[str, Any]]:
        session_id = _required_str(payload, "sessionId", "session_id")
        command_id = _required_str(payload, "clientCommandId", "client_command_id")
        session = _get_public_session(context, session_id)
        _ensure_owner(context, session.get("user_id"))
        session = _refresh_stale_running_guard(context, session)
        _ensure_session_idle(session)
        history = compact_conversation_history(build_conversation_history(context.websocket.app.state.session_store.list_messages(session_id)))
        updated = _patch_public_session_metadata(
            context.websocket.app.state.session_store,
            owner_key=context.auth.user_id,
            session_id=session_id,
            metadata_patch={
                "compaction_count": int((session.get("metadata") or {}).get("compaction_count") or 0) + 1,
                "last_compacted_at": utc_now().isoformat(),
            },
            bump_history_version=True,
        )
        return (
            "session.updated",
            {
                "session_id": session_id,
                "client_command_id": command_id,
                "history_version": updated.get("history_version"),
                "history_preview": history,
                "messages": [_message_payload(message) for message in context.websocket.app.state.session_store.list_messages(session_id)],
            },
        )

    async def _session_update(self, payload: dict[str, Any], context: WebSocketCommandContext) -> tuple[str, dict[str, Any]]:
        session_id = _required_str(payload, "sessionId", "session_id")
        command_id = _required_str(payload, "clientCommandId", "client_command_id")
        title = _optional_str(payload.get("title"))
        metadata_patch = payload.get("metadataPatch", payload.get("metadata_patch"))
        if metadata_patch is not None and not isinstance(metadata_patch, dict):
            raise WebSocketCommandError("invalid_payload", "metadataPatch must be an object")
        if metadata_patch:
            _validate_metadata_patch(metadata_patch)
        signature = _session_command_signature("session.update", {"title": title, "metadataPatch": metadata_patch})
        replay = self._replay_session_command(context, session_id=session_id, command_id=command_id, signature=signature)
        if replay is not None:
            return replay
        session = _get_public_session(context, session_id)
        _ensure_owner(context, session.get("user_id"))
        session = _refresh_stale_running_guard(context, session)
        _ensure_session_idle(session)
        if title:
            try:
                _update_public_session_title(context.websocket.app.state.session_store, owner_key=context.auth.user_id, session_id=session_id, title=title)
            except ValueError as error:
                raise WebSocketCommandError("conflict", str(error), retryable=True) from error
            except PermissionError as error:
                raise WebSocketCommandError("forbidden", "forbidden") from error
            except KeyError as error:
                raise WebSocketCommandError("not_found", "session not found") from error
        if metadata_patch:
            _patch_public_session_metadata(
                context.websocket.app.state.session_store,
                owner_key=context.auth.user_id,
                session_id=session_id,
                metadata_patch=dict(metadata_patch),
                bump_history_version=True,
            )
        session = _get_public_session(context, session_id)
        response = (
            "session.updated",
            {
                "session_id": session_id,
                "client_command_id": command_id,
                "history_version": session.get("history_version"),
                "session": _public_session_payload(session, context=context),
                "messages": [_message_payload(message) for message in context.websocket.app.state.session_store.list_messages(session_id)],
            },
        )
        self._remember_session_command(context, session_id=session_id, command_id=command_id, signature=signature, response=response)
        return response

    async def _session_archive(self, payload: dict[str, Any], context: WebSocketCommandContext) -> tuple[str, dict[str, Any]]:
        session_id = _required_str(payload, "sessionId", "session_id")
        command_id = _required_str(payload, "clientCommandId", "client_command_id")
        archived = bool(payload.get("archived", True))
        signature = _session_command_signature("session.archive", {"archived": archived})
        replay = self._replay_session_command(context, session_id=session_id, command_id=command_id, signature=signature)
        if replay is not None:
            return replay
        session = _get_public_session(context, session_id)
        _ensure_owner(context, session.get("user_id"))
        session = _refresh_stale_running_guard(context, session)
        _ensure_session_idle(session)
        try:
            updated = context.websocket.app.state.session_store.archive_session(
                owner_key=context.auth.user_id,
                session_id=session_id,
                archived=archived,
            )
        except ValueError as error:
            raise WebSocketCommandError("conflict", str(error), retryable=True) from error
        except PermissionError as error:
            raise WebSocketCommandError("forbidden", "forbidden") from error
        except KeyError as error:
            raise WebSocketCommandError("not_found", "session not found") from error
        response = (
            "session.archived",
            {
                "session_id": session_id,
                "client_command_id": command_id,
                "archived": bool(updated.get("archived_at")),
                "session": _public_session_payload(updated, context=context),
            },
        )
        self._remember_session_command(context, session_id=session_id, command_id=command_id, signature=signature, response=response)
        return response

    async def _session_delete(self, payload: dict[str, Any], context: WebSocketCommandContext) -> tuple[str, dict[str, Any]]:
        session_id = _required_str(payload, "sessionId", "session_id")
        command_id = _required_str(payload, "clientCommandId", "client_command_id")
        signature = _session_command_signature("session.delete", {})
        replay = self._replay_session_command(context, session_id=session_id, command_id=command_id, signature=signature)
        if replay is not None:
            return replay
        session = _get_public_session(context, session_id, allow_deleted=True)
        _ensure_owner(context, session.get("user_id"))
        session = _refresh_stale_running_guard(context, session)
        _ensure_session_idle(session)
        try:
            deleted = context.websocket.app.state.session_store.delete_session(
                owner_key=context.auth.user_id,
                session_id=session_id,
                deleted_by=context.auth.user_id,
            )
        except ValueError as error:
            raise WebSocketCommandError("conflict", str(error), retryable=True) from error
        except PermissionError as error:
            raise WebSocketCommandError("forbidden", "forbidden") from error
        except KeyError as error:
            raise WebSocketCommandError("not_found", "session not found") from error
        response = (
            "session.deleted",
            {
                "session_id": session_id,
                "client_command_id": command_id,
                "deleted_at": deleted.get("deleted_at"),
                "purge_after": deleted.get("purge_after"),
            },
        )
        self._remember_session_command(context, session_id=session_id, command_id=command_id, signature=signature, response=response)
        return response

    async def _session_settings_update(self, payload: dict[str, Any], context: WebSocketCommandContext) -> tuple[str, dict[str, Any]]:
        session_id = _required_str(payload, "sessionId", "session_id")
        command_id = _required_str(payload, "clientCommandId", "client_command_id")
        settings_payload = payload.get("settings")
        if not isinstance(settings_payload, dict):
            raise WebSocketCommandError("invalid_payload", "settings must be an object")
        settings = _normalize_session_settings(settings_payload)
        signature = _session_command_signature("session.settings.update", settings)
        replay = self._replay_session_command(context, session_id=session_id, command_id=command_id, signature=signature)
        if replay is not None:
            return replay
        session = _get_public_session(context, session_id)
        _ensure_owner(context, session.get("user_id"))
        session = _refresh_stale_running_guard(context, session)
        _ensure_session_idle(session)
        try:
            updated = context.websocket.app.state.session_store.update_session_settings(
                owner_key=context.auth.user_id,
                session_id=session_id,
                settings=settings,
            )
        except ValueError as error:
            raise WebSocketCommandError("conflict", str(error), retryable=True) from error
        except PermissionError as error:
            raise WebSocketCommandError("forbidden", "forbidden") from error
        except KeyError as error:
            raise WebSocketCommandError("not_found", "session not found") from error
        response = (
            "session.settings.updated",
            {
                "session_id": session_id,
                "client_command_id": command_id,
                "settings": dict(updated.get("settings") or settings),
                "session": _public_session_payload(updated, context=context),
            },
        )
        self._remember_session_command(context, session_id=session_id, command_id=command_id, signature=signature, response=response)
        return response

    async def _model_options(self, payload: dict[str, Any], context: WebSocketCommandContext) -> tuple[str, dict[str, Any]]:
        session_id = _optional_str(payload.get("sessionId", payload.get("session_id")))
        current_model = None
        if session_id:
            session = _get_public_session(context, session_id)
            _ensure_owner(context, session.get("user_id"))
            current_model = (_session_settings_snapshot(session).get("model") or session.get("model"))
        settings = context.websocket.app.state.settings
        default_model = str(current_model or getattr(settings, "openai_response_model", "") or "gpt-5.4-mini")
        model_ids = await _list_openai_models_for_user(
            context.websocket.app.state,
            user_id=context.auth.user_id,
            fallback_model=default_model,
        )
        provider_models = [
            {
                "id": model_id,
                "label": model_id,
                "provider": "openai_api_key",
                "is_current": model_id == current_model or (current_model is None and model_id == default_model),
            }
            for model_id in model_ids
        ]
        providers = [
            {
                "slug": "openai_api_key",
                "provider_name": "openai_api_key",
                "models": provider_models,
                "is_current": any(model["is_current"] for model in provider_models),
                "total_models": len(provider_models),
                "warning": None,
                "health": {"provider_name": "openai_api_key", "configured": True, "connected": True},
            }
        ]
        gemini_models = [
            {
                "id": model_id,
                "label": model_id,
                "provider": "gemini_api_key",
                "is_current": model_id == current_model,
            }
            for model_id in ("gemini-2.5-pro", "gemini-2.5-flash")
        ]
        providers.append(
            {
                "slug": "gemini_api_key",
                "provider_name": "gemini_api_key",
                "models": gemini_models,
                "is_current": any(model["is_current"] for model in gemini_models),
                "total_models": len(gemini_models),
                "warning": None,
                "health": {"provider_name": "gemini_api_key", "configured": True, "connected": True},
            }
        )
        return ("model.options.result", {"model": default_model, "providers": providers, "models": provider_models})

    async def _task_runs_active_list(self, payload: dict[str, Any], context: WebSocketCommandContext) -> tuple[str, dict[str, Any]]:
        session_id = _optional_str(payload.get("sessionId", payload.get("session_id")))
        repository = context.websocket.app.state.repository
        projection = getattr(context.websocket.app.state, "task_projection_store", None)
        items_by_task_run_id: dict[str, dict[str, Any]] = {}

        if projection is not None and session_id:
            for task_run_id in projection.list_active_task_ids(session_key=session_id):
                task = projection.get_task_snapshot(task_run_id)
                canonical_task = repository.get_task(task_run_id)
                if canonical_task is None or str(canonical_task.owner_key) != str(context.auth.user_id):
                    continue
                if not _is_live_active_task(repository, canonical_task):
                    continue
                steps = _projection_steps(projection, canonical_task.task_run_id)
                items_by_task_run_id[canonical_task.task_run_id] = _active_task_payload(
                    canonical_task,
                    steps,
                    source="active",
                    repository=repository,
                )

        total = repository.count_tasks_by_statuses(
            _ACTIVE_TASK_STATUSES,
            session_key=session_id,
            owner_key=context.auth.user_id,
        )
        for task in repository.list_tasks_by_statuses(
            _ACTIVE_TASK_STATUSES,
            session_key=session_id,
            owner_key=context.auth.user_id,
            limit=max(total, 1),
            offset=0,
        ):
            if task.task_run_id in items_by_task_run_id or str(task.owner_key) != str(context.auth.user_id):
                continue
            if not _is_live_active_task(repository, task):
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
        task_payload = _jsonable(task)
        task_payload["displayContext"] = build_task_display_context(task)
        snapshot = {
            "task": task_payload,
            "task_run": task_payload,
            "pending_approval": pending_approval,
            "approvals": [pending_approval] if pending_approval is not None else [],
            "events": events,
            "activity_items": build_activity_transcript(events),
            "activityItems": build_activity_transcript(events),
        }
        if include_steps:
            step_payloads = [_step_payload_with_display_context(task, step) for step in steps]
            snapshot["steps"] = step_payloads
            snapshot["step_runs"] = step_payloads
        if include_flow:
            snapshot["flow"] = {
                "task_run_id": task.task_run_id,
                "current_step_run_id": task.current_step_run_id,
                "nodes": [_step_payload_with_display_context(task, step) for step in steps],
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
        activity_items = build_activity_transcript(events)
        return (
            "taskRun.events.replay.result",
            {
                "task_run_id": task_run_id,
                "events": events,
                "activity_items": activity_items,
                "activityItems": activity_items,
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
        approval = context.websocket.app.state.repository.get_open_approval(task_run_id)
        if approval is None or str(approval.get("approval_id") or "") != approval_id:
            raise WebSocketCommandError("conflict", "approval is not pending for this task")

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
            streaming_message_id = f"streaming:{task.task_run_id}"

            async def _token_sink(delta: str) -> None:
                try:
                    await context.send_json(
                        _event_frame(
                            "session.message.delta",
                            {
                                "session_id": session_id,
                                "message_id": streaming_message_id,
                                "task_run_id": task.task_run_id,
                                "delta": delta,
                            },
                        )
                    )
                except Exception:
                    pass

            completed_task = await context.websocket.app.state.task_engine._execute_initial(
                task=task,
                handler=handler,
                resume_payload=None,
                token_sink=_token_sink,
            )
            await self._finish_created_message_task(
                context=context,
                session_id=session_id,
                user_message_id=user_message_id,
                task=task,
                completed_task=completed_task,
            )
        except Exception:
            logger.exception("session.message.create background 실행에 실패했습니다.")
            _mark_ws_linked_work_run_failed(context, task=task)
            try:
                context.websocket.app.state.session_store.clear_stale_running_task(
                    owner_key=task.owner_key,
                    session_id=session_id,
                    task_run_id=task.task_run_id,
                )
            except Exception:
                logger.exception("session.message.create 실패 후 running guard 정리에 실패했습니다.")
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

    async def _finish_created_message_task(
        self,
        *,
        context: WebSocketBackgroundContext,
        session_id: str,
        user_message_id: int,
        task: Any,
        completed_task: Any,
    ) -> None:
            completed_status = str(completed_task.status)
            completion_expected_version = int((task.input_payload or {}).get("completion_expected_version") or 0)
            if completed_status == TaskStatus.WAITING.value:
                # WAITING은 사용자가 볼 최종 assistant 응답이 아니라 approval 대기 상태다.
                # running guard를 유지해야 resume이 같은 task ownership으로 이어진다.
                await context.send_json(
                    _event_frame(
                        "session.message.waiting",
                        {
                            "session_id": session_id,
                            "message_id": f"waiting:{completed_task.task_run_id}",
                            "user_message_id": str(user_message_id),
                            "task_run_id": completed_task.task_run_id,
                            "status": completed_status,
                            "pending_approval": _pending_approval_payload(
                                context.websocket.app.state.repository.get_open_approval(completed_task.task_run_id)
                            ),
                        },
                    )
                )
                return
            if completed_status != TaskStatus.COMPLETED.value:
                _apply_ws_linked_work_result(context, task=completed_task)
                context.websocket.app.state.session_store.clear_stale_running_task(
                    owner_key=completed_task.owner_key,
                    session_id=session_id,
                    task_run_id=completed_task.task_run_id,
                )
                await context.send_json(
                    _event_frame(
                        "session.message.failed",
                        {
                            "session_id": session_id,
                            "message_id": f"failed:{completed_task.task_run_id}",
                            "user_message_id": str(user_message_id),
                            "task_run_id": completed_task.task_run_id,
                            "status": completed_status,
                            "error": {
                                "code": "task_not_completed",
                                "message": _assistant_content_from_task(completed_task),
                                "retryable": completed_status in {TaskStatus.FAILED.value, TaskStatus.CANCELED.value},
                            },
                        },
                    )
                )
                return
            _apply_ws_linked_work_result(context, task=completed_task)
            content = _assistant_content_from_task(completed_task)
            assistant_append = context.websocket.app.state.session_store.append_assistant_message_and_finish_task(
                owner_key=completed_task.owner_key,
                session_id=session_id,
                task_run_id=completed_task.task_run_id,
                content=content,
                completion_expected_version=completion_expected_version,
                status=completed_status,
            )
            await context.send_json(
                _event_frame(
                    "taskRun.snapshot.result",
                    _task_snapshot_payload(completed_task),
                )
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
                            stored_ref=assistant_append["message_id"],
                        ),
                        "content": content,
                        "task_run_id": completed_task.task_run_id,
                        "status": completed_status,
                        "finish_reason": "stop",
                        "history_version": assistant_append["completion_result_version"],
                    },
                )
            )
            # memory writeback / mark_used는 사용자가 이미 응답을 받은 뒤의 부가 작업이다.
            # 응답 경로를 블로킹하지 않도록 fire-and-forget 백그라운드 태스크로 분리한다.
            session = context.websocket.app.state.session_store.get_session(session_id) or {}
            _snapshot_task_ref = completed_task
            _snapshot_session_id = session_id
            _snapshot_user_message_id = user_message_id
            _snapshot_assistant_message_id = str(assistant_append["message_id"])
            _snapshot_content = content
            _snapshot_session = dict(session)

            async def _background_memory() -> None:
                try:
                    wb = await writeback_persistent_memory_candidates(
                        app_state=context.websocket.app.state,
                        user_id=str(_snapshot_task_ref.owner_key),
                        user_message=str((_snapshot_task_ref.input_payload or {}).get("prompt") or ""),
                        assistant_message=_snapshot_content,
                        session_id=_snapshot_session_id,
                        workspace_key=str(_snapshot_session.get("workspace_key") or "") or None,
                        task_run_id=_snapshot_task_ref.task_run_id,
                        user_message_id=str(_snapshot_user_message_id),
                        assistant_message_id=_snapshot_assistant_message_id,
                        model=str((_snapshot_task_ref.input_payload or {}).get("model") or "") or None,
                        provider_name=str(
                            (_snapshot_task_ref.input_payload or {}).get("provider_name")
                            or (_snapshot_task_ref.input_payload or {}).get("providerName")
                            or ""
                        ) or None,
                    )
                    mu = await mark_used_recalled_memories(
                        app_state=context.websocket.app.state,
                        task_input=dict(_snapshot_task_ref.input_payload or {}),
                        user_id=str(_snapshot_task_ref.owner_key),
                        assistant_message=_snapshot_content,
                        task_run_id=_snapshot_task_ref.task_run_id,
                    )
                    attach_memory_observation_to_task(
                        task=_snapshot_task_ref,
                        repository=context.websocket.app.state.repository,
                        writeback=wb,
                        mark_used=mu,
                    )
                    # memory observation 반영 후 최종 스냅샷을 프론트에 전달한다.
                    try:
                        await context.send_json(
                            _event_frame(
                                "taskRun.snapshot.result",
                                _task_snapshot_payload(_snapshot_task_ref),
                            )
                        )
                    except Exception:
                        pass
                except Exception:
                    logger.exception("background memory writeback/mark_used 실패")

            asyncio.ensure_future(_background_memory())

    async def _run_resume_task(self, *, context: WebSocketBackgroundContext, task_run_id: str, approval_id: str, payload: dict[str, Any]) -> None:
        try:
            completed_task = await context.websocket.app.state.orchestrator.resume(task_run_id=task_run_id, approval_id=approval_id, payload=payload)
            await self._finalize_resumed_or_canceled_task(context=context, task=completed_task)
        except Exception:
            logger.exception("taskRun.resume background 실행에 실패했습니다.")

    async def _run_cancel_task(self, *, context: WebSocketBackgroundContext, task_run_id: str) -> None:
        try:
            completed_task = await context.websocket.app.state.orchestrator.cancel(task_run_id=task_run_id)
            await self._finalize_resumed_or_canceled_task(context=context, task=completed_task)
        except Exception:
            logger.exception("taskRun.cancel background 실행에 실패했습니다.")

    async def _finalize_resumed_or_canceled_task(self, *, context: WebSocketBackgroundContext, task: Any) -> None:
        session_id = str(getattr(task, "session_key", "") or "")
        if not session_id:
            return
        session_store = context.websocket.app.state.session_store
        session = session_store.get_session(session_id)
        if session is None or not _is_public_session(session):
            return
        status = str(getattr(task, "status", ""))
        if status == TaskStatus.WAITING.value:
            await context.send_json(
                _event_frame(
                    "session.message.waiting",
                    {
                        "session_id": session_id,
                        "message_id": f"waiting:{task.task_run_id}",
                        "task_run_id": task.task_run_id,
                        "status": status,
                        "pending_approval": _pending_approval_payload(
                            context.websocket.app.state.repository.get_open_approval(task.task_run_id)
                        ),
                    },
                )
            )
            return
        if status == TaskStatus.COMPLETED.value:
            content = _assistant_content_from_task(task)
            expected_version = int((getattr(task, "input_payload", {}) or {}).get("completion_expected_version") or session.get("history_version") or 0)
            assistant_append = session_store.append_assistant_message_and_finish_task(
                owner_key=str(getattr(task, "owner_key", "") or session.get("user_id") or ""),
                session_id=session_id,
                task_run_id=task.task_run_id,
                content=content,
                completion_expected_version=expected_version,
                status=status,
            )
            await context.send_json(
                _event_frame(
                    "session.message.completed",
                    {
                        "session_id": session_id,
                        "message_id": _stored_message_id(session_store, session_id=session_id, stored_ref=assistant_append["message_id"]),
                        "content": content,
                        "task_run_id": task.task_run_id,
                        "status": status,
                        "finish_reason": "stop",
                        "history_version": assistant_append["completion_result_version"],
                    },
                )
            )
            return
        session_store.clear_stale_running_task(
            owner_key=str(getattr(task, "owner_key", "") or session.get("user_id") or ""),
            session_id=session_id,
            task_run_id=task.task_run_id,
        )
        await context.send_json(
            _event_frame(
                "session.message.failed",
                {
                    "session_id": session_id,
                    "message_id": f"failed:{task.task_run_id}",
                    "task_run_id": task.task_run_id,
                    "status": status,
                    "error": {
                        "code": "task_not_completed",
                        "message": _assistant_content_from_task(task),
                        "retryable": status in {TaskStatus.FAILED.value, TaskStatus.CANCELED.value},
                    },
                },
            )
        )

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


