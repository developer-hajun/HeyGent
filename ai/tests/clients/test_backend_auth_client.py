from __future__ import annotations

import httpx
import pytest

from app.core.config import Settings
from app.clients.backend_auth import BackendAuthClient, BackendAuthVerifyError


@pytest.mark.asyncio
async def test_verify_access_token_posts_token_and_internal_header():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url) == "http://backend/internal/auth/verify"
        assert request.headers["X-Internal-Service-Token"] == "service-token"
        assert request.read() == b'{"accessToken":"user-access-token"}'
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": {
                    "userId": 1,
                    "workspaceKey": "workspace-a",
                    "scopes": ["task:read", "task:write"],
                    "tokenExpiresAt": "2026-04-29T12:00:00Z",
                },
            },
        )

    settings = Settings(
        backend_auth_verify_url="http://backend/internal/auth/verify",
        internal_service_token="service-token",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = BackendAuthClient(settings=settings, http_client=http_client)

        result = await client.verify_access_token("user-access-token")

    assert result.user_id == "1"
    assert result.workspace_key == "workspace-a"
    assert result.scopes == ["task:read", "task:write"]
    assert result.token_expires_at == "2026-04-29T12:00:00Z"


@pytest.mark.asyncio
async def test_verify_access_token_raises_on_backend_error_status():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"success": False, "message": "invalid token"})

    settings = Settings(
        backend_auth_verify_url="http://backend/internal/auth/verify",
        internal_service_token="service-token",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = BackendAuthClient(settings=settings, http_client=http_client)

        with pytest.raises(BackendAuthVerifyError, match="401"):
            await client.verify_access_token("bad-token")


@pytest.mark.asyncio
async def test_verify_access_token_raises_when_wrapper_data_missing():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"success": True})

    settings = Settings(
        backend_auth_verify_url="http://backend/internal/auth/verify",
        internal_service_token="service-token",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = BackendAuthClient(settings=settings, http_client=http_client)

        with pytest.raises(BackendAuthVerifyError, match="data"):
            await client.verify_access_token("user-access-token")


@pytest.mark.asyncio
async def test_verify_access_token_raises_when_user_id_missing():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": {
                    "workspaceKey": "workspace-a",
                    "scopes": ["task:read"],
                    "tokenExpiresAt": "2026-04-29T12:00:00Z",
                },
            },
        )

    settings = Settings(
        backend_auth_verify_url="http://backend/internal/auth/verify",
        internal_service_token="service-token",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = BackendAuthClient(settings=settings, http_client=http_client)

        with pytest.raises(BackendAuthVerifyError, match="userId"):
            await client.verify_access_token("user-access-token")
