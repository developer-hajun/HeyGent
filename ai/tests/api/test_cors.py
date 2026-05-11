from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.cors import configure_cors


def _build_client(settings: Settings) -> TestClient:
    app = FastAPI()
    configure_cors(app, settings)

    @app.post("/taskRuns")
    def create_task_run():
        return {"ok": True}

    return TestClient(app)


def test_cors_preflight_allows_configured_frontend_origin():
    client = _build_client(
        Settings(
            cors_allowed_origins=["http://localhost:5173"],
            cors_allowed_methods=["GET", "POST", "OPTIONS"],
            cors_allowed_headers=["Authorization", "Content-Type", "X-Workspace-Key"],
        )
    )

    response = client.options(
        "/taskRuns",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type,X-Workspace-Key",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["access-control-allow-credentials"] == "true"
    assert response.headers["access-control-max-age"] == "600"
    allowed_headers = response.headers["access-control-allow-headers"].lower()
    assert "authorization" in allowed_headers
    assert "content-type" in allowed_headers
    assert "x-workspace-key" in allowed_headers


def test_cors_preflight_allows_default_delete_method():
    client = _build_client(Settings(cors_allowed_origins=["http://localhost:5173"]))

    response = client.options(
        "/taskRuns",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "DELETE",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    allowed_methods = response.headers["access-control-allow-methods"]
    assert "DELETE" in allowed_methods


def test_cors_does_not_echo_unconfigured_origin():
    client = _build_client(Settings(cors_allowed_origins=["http://localhost:5173"]))

    response = client.options(
        "/taskRuns",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
