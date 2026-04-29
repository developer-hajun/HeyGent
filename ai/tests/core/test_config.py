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
