from types import SimpleNamespace

import pytest


def test_health(client):
    response = client.get("/ai/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["api_prefix"] == "/ai/api/v1"


def test_ready(client):
    response = client.get("/ai/api/v1/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["storage"]["backend"] == "postgres"
    assert body["storage"]["postgres_configured"] is True
    provider_names = [provider["provider_name"] for provider in body["providers"]]
    assert "openai_api" in provider_names
    assert "openai_oauth" in provider_names


def test_runtime_requires_redis_when_postgres_is_configured():
    from app.main import _validate_runtime_storage_settings

    settings = SimpleNamespace(postgres_dsn="postgresql://example", redis_url=None)

    with pytest.raises(RuntimeError, match="HEYGENT_REDIS_URL"):
        _validate_runtime_storage_settings(settings)
