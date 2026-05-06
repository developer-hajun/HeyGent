from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.clients.backend_auth import BackendAuthVerifyResult
from app.domain.tasks.models import StepRun, TaskRun
from tests.fakes import InMemoryTaskRepository, InMemoryTranscriptStore


class FakeBackendAuthClient:
    async def verify_access_token(self, access_token: str, *, workspace_key: str | None = None) -> BackendAuthVerifyResult:
        return BackendAuthVerifyResult(user_id=access_token, workspace_key=workspace_key)

    async def aclose(self) -> None:
        return None


@pytest.fixture(autouse=True)
def configure_test_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HEYGENT_OPENAI_AUTH_FILE", str(tmp_path / "missing-auth.json"))
    monkeypatch.setenv("HEYGENT_OPENAI_API_KEY", "")
    monkeypatch.setenv("HEYGENT_POSTGRES_DSN", "postgresql://test")
    monkeypatch.setenv("HEYGENT_REDIS_URL", "redis://test")
    monkeypatch.setenv("HEYGENT_BRIDGE_TOKEN", "")
    # 로컬 AI/.env의 WebSocket Origin 제한이 TestClient 기본 Origin을 막지 않도록
    # 테스트 런타임에서는 각 테스트가 필요한 경우에만 허용 목록을 직접 설정한다.
    monkeypatch.setenv("HEYGENT_WS_ALLOWED_ORIGINS", "")
    monkeypatch.setenv("HEYGENT_CORS_ALLOWED_ORIGINS", "")

    import app.api.http.sessions as session_routes
    import app.api.http.agent_sessions as agent_session_routes
    import app.api.http.tasks as task_routes
    import app.main as app_main

    _patch_app_runtime(app_main, monkeypatch)

    async def optional_task_user(request):
        authorization = str(request.headers.get("authorization") or "").strip()
        if not authorization:
            return None
        _scheme, _separator, token = authorization.partition(" ")
        return await request.app.state.backend_auth_client.verify_access_token(
            token.strip(),
            workspace_key=str(request.headers.get("x-workspace-key") or request.query_params.get("workspaceKey") or "").strip() or None,
        )

    async def local_session_user(request):
        authorization = str(request.headers.get("authorization") or "").strip()
        if authorization:
            _scheme, _separator, token = authorization.partition(" ")
            return await request.app.state.backend_auth_client.verify_access_token(
                token.strip(),
                workspace_key=str(request.headers.get("x-workspace-key") or request.query_params.get("workspaceKey") or "").strip() or None,
            )
        return BackendAuthVerifyResult(user_id="local-user")

    def optional_ensure_owner(user, owner_key: str | None) -> None:
        if user is None:
            return None
        if str(owner_key or "") != str(user.user_id):
            from fastapi import HTTPException

            raise HTTPException(status_code=403, detail="forbidden")
        return None

    monkeypatch.setattr(task_routes, "authenticate_http_user", optional_task_user)
    monkeypatch.setattr(task_routes, "ensure_owner", optional_ensure_owner)
    monkeypatch.setattr(session_routes, "authenticate_http_user", local_session_user)
    monkeypatch.setattr(agent_session_routes, "authenticate_http_user", optional_task_user)
    monkeypatch.setattr(agent_session_routes, "ensure_owner", optional_ensure_owner)

    def list_public_sessions(store, *, owner_key: str | None, limit: int, offset: int):
        sessions = [
            session
            for session in store.list_sessions(limit=10_000)
            if session.get("source") == "api.session" and (owner_key is None or session.get("user_id") == owner_key)
        ]
        return sessions[offset : offset + limit], len(sessions)

    monkeypatch.setattr(session_routes, "_list_public_sessions", list_public_sessions)


@pytest.fixture()
def client() -> TestClient:
    import app.main as app_main

    with TestClient(app_main.app) as test_client:
        yield test_client


def _patch_app_runtime(app_main, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.storage.redis import FakeRedis, RedisTaskProjectionStore

    real_local_tool_runtime = app_main.LocalToolRuntime

    def local_tool_runtime_without_bridge(*args, **kwargs):
        kwargs["bridge_session_manager"] = None
        return real_local_tool_runtime(*args, **kwargs)

    monkeypatch.setattr(app_main, "apply_configured_postgres_migrations", lambda **_kwargs: [])
    monkeypatch.setattr(app_main, "connect_postgres", lambda _dsn: None)
    monkeypatch.setattr(app_main, "PostgresTaskRepository", lambda _connection_factory: InMemoryTaskRepository())
    monkeypatch.setattr(app_main, "PostgresSessionStore", lambda _connection_factory: InMemoryTranscriptStore())
    monkeypatch.setattr(app_main, "build_task_projection_store", lambda **_kwargs: RedisTaskProjectionStore(FakeRedis(), ttl_seconds=60))
    monkeypatch.setattr(app_main, "BackendAuthClient", lambda settings: FakeBackendAuthClient())
    monkeypatch.setattr(app_main, "LocalToolRuntime", local_tool_runtime_without_bridge)
    build_memory_connection_registry = app_main.build_connection_registry
    monkeypatch.setattr(app_main, "build_connection_registry", lambda **_kwargs: build_memory_connection_registry(redis_url=None, ttl_seconds=60))


@pytest.fixture()
def task_run() -> TaskRun:
    return TaskRun(
        task_run_id="task_test",
        task_type="agent.loop",
        owner_key="tester",
        status="PENDING",
        title="모델 생성 요청",
        input_payload={"prompt": "hello"},
    )


@pytest.fixture()
def step_run() -> StepRun:
    return StepRun(
        step_run_id="step_test",
        task_run_id="task_test",
        step_order=1,
        step_type="agent.loop.execute",
        status="PENDING",
        title="모델 응답 생성",
        input_payload={"prompt": "hello"},
    )
