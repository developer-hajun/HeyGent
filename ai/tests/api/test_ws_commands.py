from __future__ import annotations

from app.clients.backend_auth import BackendAuthVerifyResult
from app.domain.providers.model.base import AgentMessage, AgentModelResponse
from app.domain.tasks.models import TaskRun


class FakeBackendAuthClient:
    def __init__(self, *, user_id: str = "ws-user") -> None:
        self.user_id = user_id

    async def verify_access_token(self, access_token: str, *, workspace_key: str | None = None) -> BackendAuthVerifyResult:
        return BackendAuthVerifyResult(user_id=self.user_id, workspace_key=workspace_key)


def _patch_respond(monkeypatch, text: str = "WS_COMMAND_DONE") -> None:
    def fake_respond(self, messages, tools, model, tool_choice=None):
        return AgentModelResponse(
            provider_name="openai_api",
            model=model,
            message=AgentMessage(role="assistant", content=text, tool_calls=[]),
            output_text=text,
            tool_calls=[],
            finish_reason="stop",
            metadata={"model": model},
        )

    monkeypatch.setattr("app.domain.providers.model.openai_api.OpenAIAPIProvider.respond", fake_respond)
    monkeypatch.setattr("app.domain.providers.model.openai_oauth.OpenAIOAuthProvider.respond", fake_respond)


def _patch_respond_failure(monkeypatch) -> None:
    async def fake_execute_initial(self, *, task, handler, resume_payload):
        raise RuntimeError("테스트용 background 실패")

    monkeypatch.setattr("app.domain.orchestration.agent.loop.TaskEngine._execute_initial", fake_execute_initial)


def _authenticated_socket(client, *, user_id: str = "ws-user"):
    client.app.state.backend_auth_client = FakeBackendAuthClient(user_id=user_id)
    websocket_context = client.websocket_connect("/ai/api/v1/realtime/user/ws")
    websocket = websocket_context.__enter__()
    websocket.send_json({"type": "auth.start", "accessToken": "token-secret"})
    assert websocket.receive_json()["type"] == "auth.ok"
    return websocket_context, websocket


def _receive_until(
    websocket,
    frame_type: str,
    *,
    max_frames: int = 20,
    seen_types: list[str] | None = None,
):
    for _ in range(max_frames):
        frame = websocket.receive_json()
        if seen_types is not None:
            seen_types.append(frame.get("type"))
        if frame.get("type") == frame_type:
            return frame
    raise AssertionError(f"{frame_type} frame was not received")


def test_ws_unknown_command_returns_command_error_with_request_id(client):
    context, websocket = _authenticated_socket(client)
    try:
        websocket.send_json({"protocolVersion": 1, "type": "unknown.command", "requestId": "req_error", "payload": {}})

        response = websocket.receive_json()

        assert response["type"] == "command.error"
        assert response["requestId"] == "req_error"
        assert response["error"]["code"] == "unknown_command"
    finally:
        context.__exit__(None, None, None)


def test_ws_session_message_create_returns_accepted_before_completed_and_stores_result(client, monkeypatch):
    _patch_respond(monkeypatch, text="WS_ACCEPTED_DONE")
    context, websocket = _authenticated_socket(client, user_id="ws-owner")
    try:
        websocket.send_json(
            {
                "protocolVersion": 1,
                "type": "session.message.create",
                "requestId": "req_create",
                "payload": {
                    "content": "WebSocket command 테스트",
                    "clientMessageId": "client_msg_ws_1",
                    "model": "gpt-test",
                },
            }
        )

        accepted = websocket.receive_json()
        assert accepted["type"] == "session.message.accepted"
        assert accepted["requestId"] == "req_create"
        assert accepted["payload"]["session_id"].startswith("session_")
        assert isinstance(accepted["payload"]["user_message_id"], str)
        assert accepted["payload"]["task_run_id"].startswith("task_")
        assert accepted["payload"]["assistant_message_id"] is None

        seen_types: list[str] = []
        completed = _receive_until(websocket, "session.message.completed", seen_types=seen_types)
        assert "session.message.delta" not in seen_types
        assert isinstance(completed["payload"]["message_id"], str)
        assert completed["payload"]["content"] == "WS_ACCEPTED_DONE"
        assert completed["payload"]["task_run_id"] == accepted["payload"]["task_run_id"]

        task = client.app.state.repository.get_task(accepted["payload"]["task_run_id"])
        assert task is not None
        assert "token-secret" not in str(task.input_payload)
        messages = client.app.state.session_store.list_messages(accepted["payload"]["session_id"])
        assert [message["role"] for message in messages] == ["user", "assistant"]
    finally:
        context.__exit__(None, None, None)


def test_ws_followup_message_passes_previous_public_messages_without_current_user(client, monkeypatch):
    provider_calls: list[dict] = []

    def fake_respond(self, messages, tools, model, tool_choice=None):
        provider_calls.append({"messages": messages, "tools": tools, "model": model, "tool_choice": tool_choice})
        return AgentModelResponse(
            provider_name="openai_api",
            model=model,
            message=AgentMessage(role="assistant", content="FOLLOWUP_DONE", tool_calls=[]),
            output_text="FOLLOWUP_DONE",
            tool_calls=[],
            finish_reason="stop",
            metadata={"model": model},
        )

    monkeypatch.setattr("app.domain.providers.model.openai_api.OpenAIAPIProvider.respond", fake_respond)
    monkeypatch.setattr("app.domain.providers.model.openai_oauth.OpenAIOAuthProvider.respond", fake_respond)
    context, websocket = _authenticated_socket(client, user_id="ws-followup-owner")
    try:
        session_store = client.app.state.session_store
        session_store.create_session(
            session_id="public_followup_session",
            session_key="public_followup_session",
            source="api.session",
            user_id="ws-followup-owner",
            metadata={"source": "api.session"},
        )
        session_store.append_message(
            session_id="public_followup_session",
            role="user",
            content="강남역에서 지갑 잃어버렸어",
            metadata={"source": "api.session"},
        )
        session_store.append_message(
            session_id="public_followup_session",
            role="assistant",
            content="분실물 조회 경로를 확인했습니다.",
            metadata={"source": "api.session"},
        )

        websocket.send_json(
            {
                "protocolVersion": 1,
                "type": "session.message.create",
                "requestId": "req_followup",
                "payload": {
                    "sessionId": "public_followup_session",
                    "content": "ㄴㄴ 분실물찾은거",
                    "clientMessageId": "client_msg_ws_followup",
                    "model": "gpt-test",
                },
            }
        )

        accepted = websocket.receive_json()
        _receive_until(websocket, "session.message.completed")

        task = client.app.state.repository.get_task(accepted["payload"]["task_run_id"])
        assert task is not None
        assert task.input_payload["conversation_history"] == [
            {"role": "user", "content": "강남역에서 지갑 잃어버렸어"},
            {"role": "assistant", "content": "분실물 조회 경로를 확인했습니다."},
        ]
        assert "ㄴㄴ 분실물찾은거" not in str(task.input_payload["conversation_history"])
        assert [message.role for message in provider_calls[0]["messages"][:2]] == ["user", "assistant"]
        current_user_count = sum(
            str(message.content).count("ㄴㄴ 분실물찾은거")
            for message in provider_calls[0]["messages"]
            if message.role == "user"
        )
        assert current_user_count == 1
    finally:
        context.__exit__(None, None, None)


def test_ws_session_message_create_sends_failed_frame_after_background_error(client, monkeypatch):
    _patch_respond_failure(monkeypatch)
    context, websocket = _authenticated_socket(client, user_id="ws-fail-owner")
    try:
        websocket.send_json(
            {
                "protocolVersion": 1,
                "type": "session.message.create",
                "requestId": "req_create_fail",
                "payload": {
                    "content": "실패 frame 테스트",
                    "clientMessageId": "client_msg_ws_fail",
                    "model": "gpt-test",
                },
            }
        )

        accepted = websocket.receive_json()
        failed = _receive_until(websocket, "session.message.failed")

        assert accepted["type"] == "session.message.accepted"
        assert failed["payload"]["session_id"] == accepted["payload"]["session_id"]
        assert failed["payload"]["message_id"] != str(accepted["payload"]["user_message_id"])
        assert failed["payload"]["message_id"] == f"failed:{accepted['payload']['task_run_id']}"
        assert failed["payload"]["task_run_id"] == accepted["payload"]["task_run_id"]
        assert failed["payload"]["status"] == "FAILED"
        assert failed["payload"]["error"]["code"] == "background_task_failed"
    finally:
        context.__exit__(None, None, None)


def test_ws_list_snapshot_and_replay_happy_path(client, monkeypatch):
    _patch_respond(monkeypatch, text="WS_QUERY_DONE")
    context, websocket = _authenticated_socket(client, user_id="ws-query-owner")
    try:
        websocket.send_json(
            {
                "protocolVersion": 1,
                "type": "session.message.create",
                "requestId": "req_create_query",
                "payload": {"content": "조회 테스트", "clientMessageId": "client_msg_ws_query", "model": "gpt-test"},
            }
        )
        accepted = websocket.receive_json()
        completed = _receive_until(websocket, "session.message.completed")
        session_id = accepted["payload"]["session_id"]
        task_run_id = completed["payload"]["task_run_id"]

        websocket.send_json({"protocolVersion": 1, "type": "session.list", "requestId": "req_sessions", "payload": {}})
        sessions = websocket.receive_json()
        assert sessions["type"] == "session.list.result"
        assert sessions["requestId"] == "req_sessions"
        assert [item["session_id"] for item in sessions["payload"]["items"]] == [session_id]

        websocket.send_json(
            {
                "protocolVersion": 1,
                "type": "session.messages.list",
                "requestId": "req_messages",
                "payload": {"sessionId": session_id},
            }
        )
        messages = websocket.receive_json()
        assert messages["type"] == "session.messages.list.result"
        assert messages["type"] != "session.messages.result"
        assert messages["requestId"] == "req_messages"
        assert [item["role"] for item in messages["payload"]["items"]] == ["user", "assistant"]
        assert [item["role"] for item in messages["payload"]["messages"]] == ["user", "assistant"]
        assert all(isinstance(item["message_id"], str) for item in messages["payload"]["items"])

        websocket.send_json(
            {
                "protocolVersion": 1,
                "type": "taskRun.snapshot.get",
                "requestId": "req_snapshot",
                "payload": {"taskRunId": task_run_id, "includeSteps": True},
            }
        )
        snapshot = websocket.receive_json()
        assert snapshot["type"] == "taskRun.snapshot.result"
        assert snapshot["requestId"] == "req_snapshot"
        assert snapshot["payload"]["task"]["task_run_id"] == task_run_id
        assert snapshot["payload"]["task_run"]["task_run_id"] == task_run_id
        assert snapshot["payload"]["steps"] == []
        assert snapshot["payload"]["step_runs"] == []
        assert snapshot["payload"]["approvals"] == []
        assert snapshot["payload"]["events"]
        assert snapshot["payload"]["events"][0]["task_run_id"] == task_run_id

        websocket.send_json(
            {
                "protocolVersion": 1,
                "type": "taskRun.events.replay",
                "requestId": "req_replay",
                "payload": {"taskRunId": task_run_id, "afterSequence": 0},
            }
        )
        replay = websocket.receive_json()
        assert replay["type"] == "taskRun.events.replay.result"
        assert replay["requestId"] == "req_replay"
        assert replay["payload"]["events"]
        assert replay["payload"]["events"][0]["task_run_id"] == task_run_id
    finally:
        context.__exit__(None, None, None)


def test_ws_task_runs_active_list_filters_authenticated_owner(client):
    client.app.state.backend_auth_client = FakeBackendAuthClient(user_id="active-owner")
    client.app.state.repository.create_task(
        TaskRun(
            task_run_id="task_active_ws_owner",
            task_type="agent.loop",
            owner_key="active-owner",
            session_key="session_active_ws",
            status="RUNNING",
            title="active command",
        )
    )
    client.app.state.repository.create_task(
        TaskRun(
            task_run_id="task_active_ws_other",
            task_type="agent.loop",
            owner_key="other-owner",
            session_key="session_active_ws",
            status="RUNNING",
            title="other command",
        )
    )

    with client.websocket_connect("/ai/api/v1/realtime/user/ws") as websocket:
        websocket.send_json({"type": "auth.start", "accessToken": "token-secret"})
        websocket.receive_json()
        websocket.send_json(
            {
                "protocolVersion": 1,
                "type": "taskRuns.active.list",
                "requestId": "req_active",
                "payload": {"sessionId": "session_active_ws"},
            }
        )

        response = websocket.receive_json()

    assert response["type"] == "taskRuns.active.list.result"
    assert response["type"] != "taskRuns.active.result"
    assert response["requestId"] == "req_active"
    assert [item["task_run_id"] for item in response["payload"]["items"]] == ["task_active_ws_owner"]
    assert [item["task_run_id"] for item in response["payload"]["task_runs"]] == ["task_active_ws_owner"]


def test_ws_session_undo_rejects_when_session_is_running(client):
    context, websocket = _authenticated_socket(client, user_id="undo-owner")
    try:
        store = client.app.state.session_store
        store.create_session(
            session_id="undo_running_session",
            session_key="undo_running_session",
            source="api.session",
            user_id="undo-owner",
            metadata={"source": "api.session"},
        )
        store.append_user_message_and_start_task(
            owner_key="undo-owner",
            session_id="undo_running_session",
            content="실행 중 메시지",
            client_message_id="client_undo_running",
            task_run_id="task_undo_running",
            base_history_version=0,
        )
        client.app.state.repository.create_task(
            TaskRun(
                task_run_id="task_undo_running",
                task_type="agent.loop",
                owner_key="undo-owner",
                session_key="undo_running_session",
                status="RUNNING",
                title="실행 중",
            )
        )

        websocket.send_json(
            {
                "protocolVersion": 1,
                "type": "session.message.undo",
                "requestId": "req_undo_running",
                "payload": {
                    "sessionId": "undo_running_session",
                    "clientCommandId": "cmd_undo_running",
                },
            }
        )

        response = websocket.receive_json()

        assert response["type"] == "command.error"
        assert response["error"]["code"] == "conflict"
    finally:
        context.__exit__(None, None, None)


def test_ws_session_retry_reuses_last_user_message_without_duplicate_user_append(client, monkeypatch):
    _patch_respond(monkeypatch, text="RETRY_DONE")
    context, websocket = _authenticated_socket(client, user_id="retry-owner")
    try:
        store = client.app.state.session_store
        store.create_session(
            session_id="retry_session",
            session_key="retry_session",
            source="api.session",
            user_id="retry-owner",
            metadata={"source": "api.session"},
        )
        user_message_id = store.append_message(
            session_id="retry_session",
            role="user",
            content="강남역 분실물 다시 확인해줘",
            metadata={"source": "api.session"},
        )
        store.append_message(
            session_id="retry_session",
            role="assistant",
            content="이전 답변",
            metadata={"source": "api.session", "task_run_id": "task_old_retry"},
        )

        websocket.send_json(
            {
                "protocolVersion": 1,
                "type": "session.message.retry",
                "requestId": "req_retry",
                "payload": {
                    "sessionId": "retry_session",
                    "targetMessageId": str(user_message_id),
                    "clientCommandId": "cmd_retry",
                },
            }
        )

        accepted = websocket.receive_json()
        completed = _receive_until(websocket, "session.message.completed")
        messages = store.list_messages("retry_session")

        assert accepted["type"] == "session.message.accepted"
        assert completed["payload"]["content"] == "RETRY_DONE"
        assert [message["role"] for message in messages] == ["user", "assistant"]
        assert [message["content"] for message in messages] == [
            "강남역 분실물 다시 확인해줘",
            "RETRY_DONE",
        ]
    finally:
        context.__exit__(None, None, None)


def test_ws_session_retry_clears_running_guard_when_task_creation_fails(client, monkeypatch):
    context, websocket = _authenticated_socket(client, user_id="retry-fail-owner")
    try:
        store = client.app.state.session_store
        store.create_session(
            session_id="retry_fail_session",
            session_key="retry_fail_session",
            source="api.session",
            user_id="retry-fail-owner",
            metadata={"source": "api.session"},
        )
        user_message_id = store.append_message(
            session_id="retry_fail_session",
            role="user",
            content="실패해도 guard는 정리한다",
            metadata={"source": "api.session"},
        )
        store.append_message(
            session_id="retry_fail_session",
            role="assistant",
            content="이전 답변",
            metadata={"source": "api.session", "task_run_id": "task_old_retry_fail"},
        )

        def fail_create_task(task):
            raise RuntimeError("create_task failed")

        monkeypatch.setattr(client.app.state.repository, "create_task", fail_create_task)

        websocket.send_json(
            {
                "protocolVersion": 1,
                "type": "session.message.retry",
                "requestId": "req_retry_fail",
                "payload": {
                    "sessionId": "retry_fail_session",
                    "targetMessageId": str(user_message_id),
                    "clientCommandId": "cmd_retry_fail",
                },
            }
        )

        response = websocket.receive_json()

        assert response["type"] == "command.error"
        assert response["error"]["code"] == "internal_error"
        assert store.get_session("retry_fail_session")["running_task_run_id"] is None
    finally:
        context.__exit__(None, None, None)


def test_ws_subscribe_task_preserves_request_id_when_provided(client):
    client.app.state.backend_auth_client = FakeBackendAuthClient(user_id="subscribe-owner")
    client.app.state.repository.create_task(
        TaskRun(
            task_run_id="task_subscribe_request_id",
            task_type="agent.loop",
            owner_key="subscribe-owner",
            status="RUNNING",
            title="subscribe command",
        )
    )

    with client.websocket_connect("/ai/api/v1/realtime/user/ws") as websocket:
        websocket.send_json({"type": "auth.start", "accessToken": "token-secret"})
        websocket.receive_json()
        websocket.send_json({"type": "subscribe.task", "requestId": "req_subscribe", "taskRunId": "task_subscribe_request_id"})

        response = websocket.receive_json()

    assert response["type"] == "subscribed"
    assert response["requestId"] == "req_subscribe"
    assert response["taskRunId"] == "task_subscribe_request_id"
