from __future__ import annotations

import pytest
from starlette.websockets import WebSocketDisconnect

from app.clients.backend_auth import BackendAuthVerifyError, BackendAuthVerifyResult


class FakeBackendAuthClient:
    def __init__(self, *, user_id: str = "123", fail: bool = False) -> None:
        self.user_id = user_id
        self.fail = fail
        self.calls: list[str] = []

    async def verify_access_token(self, access_token: str) -> BackendAuthVerifyResult:
        self.calls.append(access_token)
        if self.fail:
            raise BackendAuthVerifyError("테스트용 인증 실패")
        return BackendAuthVerifyResult(user_id=self.user_id)


def test_subscribe_all_before_auth_is_rejected(client):
    client.app.state.backend_auth_client = FakeBackendAuthClient()

    with client.websocket_connect("/api/v1/gateway/ws?session_id=user:spoof") as websocket:
        websocket.send_json({"action": "subscribe_all"})

        response = websocket.receive_json()

        assert response == {"type": "auth.required"}
        assert client.app.state.session_registry.get_subscriptions("user:spoof") == set()


def test_subscribe_before_auth_is_rejected(client):
    client.app.state.backend_auth_client = FakeBackendAuthClient()

    with client.websocket_connect("/api/v1/gateway/ws") as websocket:
        websocket.send_json({"action": "subscribe", "task_run_id": "task_1"})

        response = websocket.receive_json()

        assert response == {"type": "auth.required"}
        assert client.app.state.session_registry.get_subscriptions("user:123") == set()


def test_auth_success_uses_backend_user_id_for_session(client):
    fake_auth = FakeBackendAuthClient(user_id="42")
    client.app.state.backend_auth_client = fake_auth

    with client.websocket_connect("/api/v1/gateway/ws?session_id=user:spoof") as websocket:
        websocket.send_json({"action": "auth", "accessToken": "valid-token"})
        websocket.send_json({"action": "subscribe", "task_run_id": "task_1"})

        auth_response = websocket.receive_json()

        assert fake_auth.calls == ["valid-token"]
        assert auth_response == {"type": "auth.ok", "userId": "42"}
        subscribe_response = websocket.receive_json()
        assert subscribe_response == {"type": "subscribed", "task_run_id": "task_1"}
        assert client.app.state.session_registry.get_subscriptions("user:42") == {"task:task_1"}
        assert client.app.state.session_registry.get_subscriptions("user:spoof") == set()


def test_authenticated_session_cleanup_runs_on_disconnect(client):
    fake_auth = FakeBackendAuthClient(user_id="77")
    client.app.state.backend_auth_client = fake_auth

    with client.websocket_connect("/api/v1/gateway/ws") as websocket:
        websocket.send_json({"action": "auth", "accessToken": "valid-token"})
        websocket.receive_json()
        websocket.send_json({"action": "subscribe", "task_run_id": "task_cleanup"})
        websocket.receive_json()

    assert client.app.state.session_registry.get_subscriptions("user:77") == set()


def test_auth_failure_sends_failed_and_closes(client):
    fake_auth = FakeBackendAuthClient(fail=True)
    client.app.state.backend_auth_client = fake_auth

    with client.websocket_connect("/api/v1/ws") as websocket:
        websocket.send_json({"action": "auth", "accessToken": "bad-token"})
        websocket.send_json({"action": "ping"})

        response = websocket.receive_json()

        assert fake_auth.calls == ["bad-token"]
        assert response == {"type": "auth.failed"}
        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()
