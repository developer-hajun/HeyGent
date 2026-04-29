from __future__ import annotations

from app.core.config import get_settings


def test_backend_auth_verify_defaults_to_local_backend(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("HEYGENT_BACKEND_AUTH_VERIFY_URL", raising=False)
    monkeypatch.delenv("HEYGENT_INTERNAL_SERVICE_TOKEN", raising=False)

    settings = get_settings()

    assert settings.backend_auth_verify_url == "http://127.0.0.1:8080/api/v1/internal/auth/verify"
    assert settings.internal_service_token is None


def test_backend_auth_verify_settings_read_environment(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HEYGENT_BACKEND_AUTH_VERIFY_URL", "http://backend/internal/auth/verify")
    monkeypatch.setenv("HEYGENT_INTERNAL_SERVICE_TOKEN", "service-token")

    settings = get_settings()

    assert settings.backend_auth_verify_url == "http://backend/internal/auth/verify"
    assert settings.internal_service_token == "service-token"


def test_redis_connection_registry_settings_read_environment(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HEYGENT_REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("HEYGENT_WS_CONNECTION_TTL_SECONDS", "120")
    monkeypatch.setenv("HEYGENT_TASK_PROJECTION_TTL_SECONDS", "1800")
    monkeypatch.setenv("HEYGENT_TASK_PROJECTION_MAX_EVENTS", "50")

    settings = get_settings()

    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.ws_connection_ttl_seconds == 120
    assert settings.task_projection_ttl_seconds == 1800
    assert settings.task_projection_max_events == 50
