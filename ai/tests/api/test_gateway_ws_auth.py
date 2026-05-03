from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from starlette.websockets import WebSocketDisconnect

from app.api.router import build_api_router
from app.api.ws.gateway import (
    WebSocketAuthRateLimiter,
    _authenticate_first_message,
    _client_message_action,
    _client_task_run_id,
)
from app.clients.backend_auth import BackendAuthVerifyError, BackendAuthVerifyResult
from app.core.config import Settings, get_settings
from app.contracts.event.task_events import TaskEventEnvelope
from app.domain.tasks.models import TaskRun
from app.storage.redis import FakeRedis, RedisTaskProjectionStore


class FakeBackendAuthClient:
    def __init__(self, *, user_id: str = "123", fail: bool = False) -> None:
        self.user_id = user_id
        self.fail = fail
        self.calls: list[str] = []
        self.workspace_keys: list[str | None] = []

    async def verify_access_token(self, access_token: str, *, workspace_key: str | None = None) -> BackendAuthVerifyResult:
        self.calls.append(access_token)
        self.workspace_keys.append(workspace_key)
        if self.fail:
            raise BackendAuthVerifyError("테스트용 인증 실패")
        return BackendAuthVerifyResult(user_id=self.user_id, workspace_key=workspace_key)


class FakeConnectionRegistry:
    def __init__(self, *, fail_register: bool = False, fail_unregister: bool = False) -> None:
        self.fail_register = fail_register
        self.fail_unregister = fail_unregister
        self.registered: list[dict[str, str]] = []
        self.touched: list[dict[str, str]] = []
        self.unregistered: list[dict[str, str]] = []

    async def register_connection(self, *, connection_id: str, user_id: str, session_id: str) -> None:
        if self.fail_register:
            raise RuntimeError("테스트용 등록 실패")
        self.registered.append(
            {"connection_id": connection_id, "user_id": user_id, "session_id": session_id}
        )

    async def touch_connection(self, *, connection_id: str, user_id: str, session_id: str) -> None:
        self.touched.append({"connection_id": connection_id, "user_id": user_id, "session_id": session_id})

    async def unregister_connection(self, *, connection_id: str, user_id: str, session_id: str) -> None:
        if self.fail_unregister:
            raise RuntimeError("테스트용 정리 실패")
        self.unregistered.append(
            {"connection_id": connection_id, "user_id": user_id, "session_id": session_id}
        )


class SlowFirstMessageWebSocket:
    def __init__(self) -> None:
        self.app = SimpleNamespace(
            state=SimpleNamespace(
                backend_auth_client=FakeBackendAuthClient(),
                settings=SimpleNamespace(ws_auth_first_message_timeout_seconds=0.01),
            )
        )
        self.sent: list[dict[str, str]] = []
        self.closed_code: int | None = None

    async def receive_json(self) -> dict[str, str]:
        await asyncio.sleep(1)
        return {"type": "auth.start", "accessToken": "too-late"}

    async def send_json(self, message: dict[str, str]) -> None:
        self.sent.append(message)

    async def close(self, *, code: int) -> None:
        self.closed_code = code


def task_for_owner(task_run_id: str, owner_key: str) -> TaskRun:
    return TaskRun(
        task_run_id=task_run_id,
        task_type="agent.loop",
        intent_type="agent.loop",
        entry_handler_key="agent.loop",
        owner_key=owner_key,
        status="RUNNING",
        title="웹소켓 테스트 작업",
    )


def test_only_canonical_realtime_websocket_path_is_registered():
    app = FastAPI()
    app.include_router(build_api_router(Settings(api_prefix="/ai/api/v1")))
    paths = {route.path for route in app.routes}

    assert "/ai/api/v1/realtime/user/ws" in paths
    assert "/ai/api/v1/gateway/ws" not in paths
    assert "/ai/api/v1/ws" not in paths


def test_legacy_websocket_message_shapes_are_not_accepted():
    assert _client_message_action({"action": "auth", "accessToken": "token"}) is None
    assert _client_message_action({"action": "ping"}) is None
    assert _client_message_action({"action": "subscribe", "task_run_id": "task_1"}) is None
    assert _client_task_run_id({"task_run_id": "task_1"}) is None


def test_settings_reads_websocket_allowed_origins(monkeypatch):
    monkeypatch.setenv("HEYGENT_WS_ALLOWED_ORIGINS", "https://app.example.com, https://admin.example.com")

    settings = get_settings()

    assert settings.ws_allowed_origins == ["https://app.example.com", "https://admin.example.com"]


def test_websocket_auth_rate_limiter_blocks_after_recent_failures():
    current_time = 1000.0
    limiter = WebSocketAuthRateLimiter(max_failures=2, window_seconds=60, clock=lambda: current_time)

    assert limiter.allowed("client-a") is True
    limiter.record_failure("client-a")
    limiter.record_failure("client-a")

    assert limiter.allowed("client-a") is False

    current_time = 1061.0

    assert limiter.allowed("client-a") is True


def test_websocket_auth_rate_limiter_resets_after_success():
    limiter = WebSocketAuthRateLimiter(max_failures=1, window_seconds=60, clock=lambda: 1000.0)

    limiter.record_failure("client-a")
    limiter.record_success("client-a")

    assert limiter.allowed("client-a") is True


@pytest.mark.asyncio
async def test_auth_first_message_timeout_closes_before_verification():
    websocket = SlowFirstMessageWebSocket()

    result = await _authenticate_first_message(websocket)

    assert result is None
    assert websocket.sent == [{"type": "auth.timeout"}]
    assert websocket.closed_code == 1008
    assert websocket.app.state.backend_auth_client.calls == []


def test_empty_websocket_allowed_origins_allows_existing_clients(client):
    client.app.state.settings.ws_allowed_origins = []
    client.app.state.backend_auth_client = FakeBackendAuthClient(user_id="42")

    with client.websocket_connect(
        "/ai/api/v1/realtime/user/ws",
        headers={"origin": "https://unconfigured.example.com"},
    ) as websocket:
        websocket.send_json({"type": "auth.start", "accessToken": "valid-token"})

        assert websocket.receive_json() == {"type": "auth.ok", "userId": "42"}


def test_realtime_user_websocket_authenticates_on_canonical_path(client):
    client.app.state.backend_auth_client = FakeBackendAuthClient(user_id="42")

    with client.websocket_connect("/ai/api/v1/realtime/user/ws") as websocket:
        websocket.send_json({"type": "auth.start", "accessToken": "valid-token"})

        assert websocket.receive_json() == {"type": "auth.ok", "userId": "42"}


def test_websocket_auth_passes_workspace_key_hint_to_backend(client):
    auth_client = FakeBackendAuthClient(user_id="42")
    client.app.state.backend_auth_client = auth_client

    with client.websocket_connect("/ai/api/v1/realtime/user/ws") as websocket:
        websocket.send_json({"type": "auth.start", "accessToken": "valid-token", "workspaceKey": "workspace-a"})

        assert websocket.receive_json() == {"type": "auth.ok", "userId": "42", "workspaceKey": "workspace-a"}
        assert auth_client.calls == ["valid-token"]
        assert auth_client.workspace_keys == ["workspace-a"]


def test_realtime_websocket_accepts_documented_type_auth_message(client):
    auth_client = FakeBackendAuthClient(user_id="42")
    client.app.state.backend_auth_client = auth_client

    with client.websocket_connect("/ai/api/v1/realtime/user/ws") as websocket:
        websocket.send_json({"type": "auth.start", "accessToken": "valid-token", "workspaceKey": "workspace-a"})

        assert websocket.receive_json() == {"type": "auth.ok", "userId": "42", "workspaceKey": "workspace-a"}
        assert auth_client.calls == ["valid-token"]
        assert auth_client.workspace_keys == ["workspace-a"]


def test_realtime_websocket_accepts_documented_ping_and_subscribe_messages(client):
    client.app.state.backend_auth_client = FakeBackendAuthClient(user_id="owner-a")
    client.app.state.repository.create_task(task_for_owner("task_1", "owner-a"))

    with client.websocket_connect("/ai/api/v1/realtime/user/ws") as websocket:
        websocket.send_json({"type": "auth.start", "accessToken": "valid-token"})
        assert websocket.receive_json() == {"type": "auth.ok", "userId": "owner-a"}

        websocket.send_json({"type": "ping"})
        assert websocket.receive_json() == {"type": "pong"}

        websocket.send_json({"type": "subscribe.task", "taskRunId": "task_1"})
        assert websocket.receive_json() == {"type": "subscribed", "taskRunId": "task_1"}


def test_websocket_rejects_origin_outside_allowed_list(client):
    client.app.state.settings.ws_allowed_origins = ["https://app.example.com"]
    client.app.state.backend_auth_client = FakeBackendAuthClient(user_id="42")

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            "/ai/api/v1/realtime/user/ws",
            headers={"origin": "https://evil.example.com"},
        ):
            pass

    assert exc_info.value.code == 1008


def test_websocket_rate_limit_blocks_repeated_auth_failures(client):
    client.app.state.settings.ws_auth_rate_limit_max_failures = 1
    client.app.state.settings.ws_auth_rate_limit_window_seconds = 60
    client.app.state.ws_auth_rate_limiter = WebSocketAuthRateLimiter(max_failures=1, window_seconds=60)
    client.app.state.backend_auth_client = FakeBackendAuthClient(fail=True)

    with client.websocket_connect("/ai/api/v1/realtime/user/ws") as websocket:
        websocket.send_json({"type": "auth.start", "accessToken": "bad-token"})
        assert websocket.receive_json() == {"type": "auth.failed"}

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ai/api/v1/realtime/user/ws"):
            pass

    assert exc_info.value.code == 1008


def test_subscribe_all_before_auth_is_rejected(client):
    client.app.state.backend_auth_client = FakeBackendAuthClient()

    with client.websocket_connect("/ai/api/v1/realtime/user/ws?session_id=user:spoof") as websocket:
        websocket.send_json({"type": "subscribe.all"})

        response = websocket.receive_json()

        assert response == {"type": "auth.required"}
        assert client.app.state.session_registry.get_subscriptions("user:spoof") == set()


def test_subscribe_all_after_auth_is_rejected_by_policy(client):
    client.app.state.backend_auth_client = FakeBackendAuthClient(user_id="owner-a")

    with client.websocket_connect("/ai/api/v1/realtime/user/ws") as websocket:
        websocket.send_json({"type": "auth.start", "accessToken": "valid-token"})
        websocket.send_json({"type": "subscribe.all"})

        assert websocket.receive_json() == {"type": "auth.ok", "userId": "owner-a"}
        assert websocket.receive_json() == {
            "type": "subscription.denied",
            "taskRunId": "all",
            "reason": "subscribe_all_disabled",
        }
        assert client.app.state.session_registry.get_subscriptions("user:owner-a") == set()


def test_subscribe_before_auth_is_rejected(client):
    client.app.state.backend_auth_client = FakeBackendAuthClient()

    with client.websocket_connect("/ai/api/v1/realtime/user/ws") as websocket:
        websocket.send_json({"type": "subscribe.task", "taskRunId": "task_1"})

        response = websocket.receive_json()

        assert response == {"type": "auth.required"}
        assert client.app.state.session_registry.get_subscriptions("user:123") == set()


def test_auth_success_uses_backend_user_id_for_session(client):
    fake_auth = FakeBackendAuthClient(user_id="42")
    client.app.state.backend_auth_client = fake_auth
    client.app.state.repository.create_task(task_for_owner("task_1", "42"))

    with client.websocket_connect("/ai/api/v1/realtime/user/ws?session_id=user:spoof") as websocket:
        websocket.send_json({"type": "auth.start", "accessToken": "valid-token"})
        websocket.send_json({"type": "subscribe.task", "taskRunId": "task_1"})

        auth_response = websocket.receive_json()

        assert fake_auth.calls == ["valid-token"]
        assert auth_response == {"type": "auth.ok", "userId": "42"}
        subscribe_response = websocket.receive_json()
        assert subscribe_response == {"type": "subscribed", "taskRunId": "task_1"}
        assert client.app.state.session_registry.get_subscriptions("user:42") == {"task:task_1"}
        assert client.app.state.session_registry.get_subscriptions("user:spoof") == set()


def test_subscribe_ack_includes_latest_sequence_when_projection_exists(client):
    fake_auth = FakeBackendAuthClient(user_id="42")
    projection = RedisTaskProjectionStore(FakeRedis(), ttl_seconds=60)
    client.app.state.backend_auth_client = fake_auth
    client.app.state.task_projection_store = projection
    projection.save_task_snapshot(task_for_owner("task_ws_latest", "42"))
    projection.append_event(
        TaskEventEnvelope(
            event_id="event_ws_latest",
            event_type="task.updated",
            task_run_id="task_ws_latest",
            producer="test",
            occurred_at="2026-04-29T00:00:00+00:00",
        )
    )

    with client.websocket_connect("/ai/api/v1/realtime/user/ws") as websocket:
        websocket.send_json({"type": "auth.start", "accessToken": "valid-token"})
        websocket.send_json({"type": "subscribe.task", "taskRunId": "task_ws_latest"})

        assert websocket.receive_json() == {"type": "auth.ok", "userId": "42"}
        subscribe_response = websocket.receive_json()

        assert subscribe_response["type"] == "subscribed"
        assert subscribe_response["taskRunId"] == "task_ws_latest"
        assert subscribe_response["latestSequence"] == 1


def test_subscribe_task_replays_events_after_client_last_sequence(client):
    fake_auth = FakeBackendAuthClient(user_id="42")
    projection = RedisTaskProjectionStore(FakeRedis(), ttl_seconds=60)
    client.app.state.backend_auth_client = fake_auth
    client.app.state.task_projection_store = projection
    projection.save_task_snapshot(task_for_owner("task_ws_replay", "42"))
    projection.append_event(
        TaskEventEnvelope(
            event_id="event_ws_replay_1",
            event_type="step.started",
            task_run_id="task_ws_replay",
            producer="test",
            occurred_at="2026-04-29T00:00:00+00:00",
        )
    )
    projection.append_event(
        TaskEventEnvelope(
            event_id="event_ws_replay_2",
            event_type="step.completed",
            task_run_id="task_ws_replay",
            producer="test",
            occurred_at="2026-04-29T00:00:01+00:00",
        )
    )

    with client.websocket_connect("/ai/api/v1/realtime/user/ws") as websocket:
        websocket.send_json({"type": "auth.start", "accessToken": "valid-token"})
        websocket.send_json(
            {
                "type": "subscribe.task",
                "requestId": "req_subscribe_replay",
                "taskRunId": "task_ws_replay",
                "lastSequence": 1,
            }
        )

        assert websocket.receive_json() == {"type": "auth.ok", "userId": "42"}
        subscribe_response = websocket.receive_json()
        replay_response = websocket.receive_json()

        assert subscribe_response["type"] == "subscribed"
        assert subscribe_response["requestId"] == "req_subscribe_replay"
        assert subscribe_response["latestSequence"] == 2
        assert replay_response["type"] == "taskRun.events.replay.result"
        assert "requestId" not in replay_response
        assert replay_response["payload"]["task_run_id"] == "task_ws_replay"
        assert [event["event_id"] for event in replay_response["payload"]["events"]] == ["event_ws_replay_2"]
        assert replay_response["payload"]["latest_sequence"] == 2


def test_subscribe_task_replay_marks_retention_gap_when_projection_trimmed(client):
    fake_auth = FakeBackendAuthClient(user_id="42")
    projection = RedisTaskProjectionStore(FakeRedis(), ttl_seconds=60, max_events=1)
    client.app.state.backend_auth_client = fake_auth
    client.app.state.task_projection_store = projection
    projection.save_task_snapshot(task_for_owner("task_ws_gap", "42"))
    projection.append_event(
        TaskEventEnvelope(
            event_id="event_ws_gap_1",
            event_type="step.started",
            task_run_id="task_ws_gap",
            producer="test",
            occurred_at="2026-04-29T00:00:00+00:00",
        )
    )
    projection.append_event(
        TaskEventEnvelope(
            event_id="event_ws_gap_2",
            event_type="step.completed",
            task_run_id="task_ws_gap",
            producer="test",
            occurred_at="2026-04-29T00:00:01+00:00",
        )
    )
    projection.trim_recent_events("task_ws_gap")

    with client.websocket_connect("/ai/api/v1/realtime/user/ws") as websocket:
        websocket.send_json({"type": "auth.start", "accessToken": "valid-token"})
        websocket.send_json(
            {
                "type": "subscribe.task",
                "taskRunId": "task_ws_gap",
                "lastSequence": 0,
            }
        )

        assert websocket.receive_json() == {"type": "auth.ok", "userId": "42"}
        subscribe_response = websocket.receive_json()
        replay_response = websocket.receive_json()

        assert subscribe_response["latestSequence"] == 2
        assert replay_response["type"] == "taskRun.events.replay.result"
        assert replay_response["payload"]["retention_exceeded"] is True
        assert replay_response["payload"]["events"][0]["event_id"] == "event_ws_gap_2"


def test_subscribe_rejects_task_owned_by_other_user_from_projection(client):
    fake_auth = FakeBackendAuthClient(user_id="owner-a")
    projection = RedisTaskProjectionStore(FakeRedis(), ttl_seconds=60)
    client.app.state.backend_auth_client = fake_auth
    client.app.state.task_projection_store = projection
    projection.save_task_snapshot(task_for_owner("task_ws_other_owner", "owner-b"))

    with client.websocket_connect("/ai/api/v1/realtime/user/ws") as websocket:
        websocket.send_json({"type": "auth.start", "accessToken": "valid-token"})
        websocket.send_json({"type": "subscribe.task", "taskRunId": "task_ws_other_owner"})

        assert websocket.receive_json() == {"type": "auth.ok", "userId": "owner-a"}
        assert websocket.receive_json() == {
            "type": "subscription.denied",
            "taskRunId": "task_ws_other_owner",
            "reason": "forbidden",
        }
        assert client.app.state.session_registry.get_subscriptions("user:owner-a") == set()
        assert client.app.state.ws_manager.directory.get("task:task_ws_other_owner") == set()


def test_subscribe_allows_owner_when_projection_snapshot_missing_but_repository_has_task(client):
    fake_auth = FakeBackendAuthClient(user_id="owner-a")
    projection = RedisTaskProjectionStore(FakeRedis(), ttl_seconds=60)
    client.app.state.backend_auth_client = fake_auth
    client.app.state.task_projection_store = projection
    client.app.state.repository.create_task(
        task_for_owner("task_ws_repo_fallback", "owner-a")
    )

    with client.websocket_connect("/ai/api/v1/realtime/user/ws") as websocket:
        websocket.send_json({"type": "auth.start", "accessToken": "valid-token"})
        websocket.send_json({"type": "subscribe.task", "taskRunId": "task_ws_repo_fallback"})

        assert websocket.receive_json() == {"type": "auth.ok", "userId": "owner-a"}
        assert websocket.receive_json() == {"type": "subscribed", "taskRunId": "task_ws_repo_fallback"}
        assert client.app.state.session_registry.get_subscriptions("user:owner-a") == {
            "task:task_ws_repo_fallback"
        }


def test_auth_success_registers_random_connection_for_backend_user(client):
    fake_auth = FakeBackendAuthClient(user_id="42")
    fake_registry = FakeConnectionRegistry()
    client.app.state.backend_auth_client = fake_auth
    client.app.state.connection_registry = fake_registry

    with client.websocket_connect("/ai/api/v1/realtime/user/ws?session_id=user:spoof") as websocket:
        websocket.send_json({"type": "auth.start", "accessToken": "valid-token"})

        assert websocket.receive_json() == {"type": "auth.ok", "userId": "42"}
        assert len(fake_registry.registered) == 1
        registered = fake_registry.registered[0]
        assert registered["user_id"] == "42"
        assert registered["session_id"] == "user:42"
        assert registered["connection_id"]
        assert "spoof" not in registered["connection_id"]


def test_auth_success_ignores_query_user_id_spoofing(client):
    fake_auth = FakeBackendAuthClient(user_id="backend-user")
    fake_registry = FakeConnectionRegistry()
    client.app.state.backend_auth_client = fake_auth
    client.app.state.connection_registry = fake_registry

    with client.websocket_connect("/ai/api/v1/realtime/user/ws?userId=attacker&session_id=user:attacker") as websocket:
        websocket.send_json({"type": "auth.start", "accessToken": "valid-token"})

        assert websocket.receive_json() == {"type": "auth.ok", "userId": "backend-user"}
        assert fake_registry.registered[0]["user_id"] == "backend-user"
        assert fake_registry.registered[0]["session_id"] == "user:backend-user"


def test_each_authenticated_connection_gets_distinct_connection_id(client):
    fake_auth = FakeBackendAuthClient(user_id="42")
    fake_registry = FakeConnectionRegistry()
    client.app.state.backend_auth_client = fake_auth
    client.app.state.connection_registry = fake_registry

    with client.websocket_connect("/ai/api/v1/realtime/user/ws") as first_websocket:
        first_websocket.send_json({"type": "auth.start", "accessToken": "valid-token"})
        first_websocket.receive_json()

    with client.websocket_connect("/ai/api/v1/realtime/user/ws") as second_websocket:
        second_websocket.send_json({"type": "auth.start", "accessToken": "valid-token"})
        second_websocket.receive_json()

    assert fake_registry.registered[0]["connection_id"] != fake_registry.registered[1]["connection_id"]


def test_auth_success_is_not_sent_when_connection_register_fails(client):
    fake_auth = FakeBackendAuthClient(user_id="42")
    fake_registry = FakeConnectionRegistry(fail_register=True)
    client.app.state.backend_auth_client = fake_auth
    client.app.state.connection_registry = fake_registry

    with client.websocket_connect("/ai/api/v1/realtime/user/ws") as websocket:
        websocket.send_json({"type": "auth.start", "accessToken": "valid-token"})

        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()


def test_authenticated_ping_refreshes_connection_ttl(client):
    fake_auth = FakeBackendAuthClient(user_id="55")
    fake_registry = FakeConnectionRegistry()
    client.app.state.backend_auth_client = fake_auth
    client.app.state.connection_registry = fake_registry

    with client.websocket_connect("/ai/api/v1/realtime/user/ws") as websocket:
        websocket.send_json({"type": "auth.start", "accessToken": "valid-token"})
        websocket.receive_json()
        websocket.send_json({"type": "ping"})

        assert websocket.receive_json() == {"type": "pong"}
        assert fake_registry.touched == [
            {
                "connection_id": fake_registry.registered[0]["connection_id"],
                "user_id": "55",
                "session_id": "user:55",
            }
        ]


def test_authenticated_session_cleanup_runs_on_disconnect(client):
    fake_auth = FakeBackendAuthClient(user_id="77")
    fake_registry = FakeConnectionRegistry()
    client.app.state.backend_auth_client = fake_auth
    client.app.state.connection_registry = fake_registry
    client.app.state.repository.create_task(task_for_owner("task_cleanup", "77"))

    with client.websocket_connect("/ai/api/v1/realtime/user/ws") as websocket:
        websocket.send_json({"type": "auth.start", "accessToken": "valid-token"})
        websocket.receive_json()
        websocket.send_json({"type": "subscribe.task", "taskRunId": "task_cleanup"})
        websocket.receive_json()

    assert client.app.state.session_registry.get_subscriptions("user:77") == set()
    assert fake_registry.unregistered == [
        {
            "connection_id": fake_registry.registered[0]["connection_id"],
            "user_id": "77",
            "session_id": "user:77",
        }
    ]


def test_unregister_failure_still_cleans_local_websocket_directory(client):
    fake_auth = FakeBackendAuthClient(user_id="77")
    fake_registry = FakeConnectionRegistry(fail_unregister=True)
    client.app.state.backend_auth_client = fake_auth
    client.app.state.connection_registry = fake_registry
    client.app.state.repository.create_task(task_for_owner("task_cleanup", "77"))

    with client.websocket_connect("/ai/api/v1/realtime/user/ws") as websocket:
        websocket.send_json({"type": "auth.start", "accessToken": "valid-token"})
        websocket.receive_json()
        websocket.send_json({"type": "subscribe.task", "taskRunId": "task_cleanup"})
        websocket.receive_json()

    assert client.app.state.ws_manager.directory.get("task:task_cleanup") == set()


def test_auth_failure_does_not_register_connection(client):
    fake_auth = FakeBackendAuthClient(fail=True)
    fake_registry = FakeConnectionRegistry()
    client.app.state.backend_auth_client = fake_auth
    client.app.state.connection_registry = fake_registry

    with client.websocket_connect("/ai/api/v1/realtime/user/ws") as websocket:
        websocket.send_json({"type": "auth.start", "accessToken": "bad-token"})

        assert websocket.receive_json() == {"type": "auth.failed"}

    assert fake_registry.registered == []


def test_auth_failure_sends_failed_and_closes(client):
    fake_auth = FakeBackendAuthClient(fail=True)
    client.app.state.backend_auth_client = fake_auth

    with client.websocket_connect("/ai/api/v1/realtime/user/ws") as websocket:
        websocket.send_json({"type": "auth.start", "accessToken": "bad-token"})
        websocket.send_json({"type": "ping"})

        response = websocket.receive_json()

        assert fake_auth.calls == ["bad-token"]
        assert response == {"type": "auth.failed"}
        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()
