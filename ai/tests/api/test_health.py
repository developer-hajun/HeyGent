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


def test_runtime_requires_redis_when_postgres_is_configured(monkeypatch):
    monkeypatch.setenv("HEYGENT_POSTGRES_DSN", "postgresql://example")
    monkeypatch.delenv("HEYGENT_REDIS_URL", raising=False)

    from app.main import _validate_runtime_storage_settings

    try:
        _validate_runtime_storage_settings()
    except RuntimeError as error:
        assert "HEYGENT_REDIS_URL" in str(error)
    else:
        raise AssertionError("AI 런타임은 Redis 설정 없이는 시작하면 안 된다.")
