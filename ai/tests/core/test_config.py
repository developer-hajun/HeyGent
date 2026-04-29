from __future__ import annotations

from app.core.config import get_settings


def test_backend_auth_verify_defaults_to_local_backend(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("HEYGENT_BACKEND_AUTH_VERIFY_URL", raising=False)
    monkeypatch.delenv("HEYGENT_INTERNAL_SERVICE_TOKEN", raising=False)

    settings = get_settings()

    assert settings.backend_auth_verify_url == "http://127.0.0.1:8080/internal/ai/auth/validate"
    assert settings.internal_service_token is None


def test_backend_auth_verify_settings_read_environment(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HEYGENT_BACKEND_AUTH_VERIFY_URL", "http://backend/internal/ai/auth/validate")
    monkeypatch.setenv("HEYGENT_INTERNAL_SERVICE_TOKEN", "service-token")

    settings = get_settings()

    assert settings.backend_auth_verify_url == "http://backend/internal/ai/auth/validate"
    assert settings.internal_service_token == "service-token"


def test_redis_connection_registry_settings_read_environment(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HEYGENT_REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("HEYGENT_WS_CONNECTION_TTL_SECONDS", "120")
    monkeypatch.setenv("HEYGENT_WS_AUTH_RATE_LIMIT_MAX_FAILURES", "3")
    monkeypatch.setenv("HEYGENT_WS_AUTH_RATE_LIMIT_WINDOW_SECONDS", "30")
    monkeypatch.setenv("HEYGENT_TASK_PROJECTION_TTL_SECONDS", "1800")
    monkeypatch.setenv("HEYGENT_TASK_PROJECTION_MAX_EVENTS", "50")

    settings = get_settings()

    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.ws_connection_ttl_seconds == 120
    assert settings.ws_auth_rate_limit_max_failures == 3
    assert settings.ws_auth_rate_limit_window_seconds == 30
    assert settings.task_projection_ttl_seconds == 1800
    assert settings.task_projection_max_events == 50


def test_postgres_settings_read_environment(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HEYGENT_POSTGRES_DSN", "postgresql://user:pass@localhost:5432/heygent")
    monkeypatch.setenv("HEYGENT_POSTGRES_MIGRATIONS_ENABLED", "false")

    settings = get_settings()

    assert settings.postgres_dsn == "postgresql://user:pass@localhost:5432/heygent"
    assert settings.postgres_migrations_enabled is False


def test_cors_settings_read_environment(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HEYGENT_CORS_ALLOWED_ORIGINS", "http://localhost:5173, https://app.example.com")
    monkeypatch.setenv("HEYGENT_CORS_ALLOWED_METHODS", "GET,POST,OPTIONS")
    monkeypatch.setenv("HEYGENT_CORS_ALLOWED_HEADERS", "Authorization,Content-Type,X-Workspace-Key")
    monkeypatch.setenv("HEYGENT_CORS_ALLOW_CREDENTIALS", "false")
    monkeypatch.setenv("HEYGENT_CORS_MAX_AGE_SECONDS", "1200")

    settings = get_settings()

    assert settings.cors_allowed_origins == ["http://localhost:5173", "https://app.example.com"]
    assert settings.cors_allowed_methods == ["GET", "POST", "OPTIONS"]
    assert settings.cors_allowed_headers == ["Authorization", "Content-Type", "X-Workspace-Key"]
    assert settings.cors_allow_credentials is False
    assert settings.cors_max_age_seconds == 1200
