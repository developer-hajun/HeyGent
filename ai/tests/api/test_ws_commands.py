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
