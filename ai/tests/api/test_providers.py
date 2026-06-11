from fastapi.testclient import TestClient

from app.main import app


def test_list_providers(client):
    response = client.get("/ai/api/v1/providers")

    assert response.status_code == 200
    providers = {item["provider_name"]: item for item in response.json()}
    assert "openai_api" in providers
    assert "openai_oauth" not in providers


def test_get_provider_detail(client):
    response = client.get("/ai/api/v1/providers/openai_api")

    assert response.status_code == 200
    body = response.json()
    assert body["provider_name"] == "openai_api"
    assert body["auth_type"] == "api_key"


def test_provider_auth_reports_missing_api_key(client, monkeypatch):
    monkeypatch.delenv("HEYGENT_OPENAI_API_KEY", raising=False)

    response = client.post("/ai/api/v1/providers/openai_api/auth", json={"force_oauth": True})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "configuration_required"
    assert body["authorization_url"] is None
    assert body["missing_env"] == ["HEYGENT_OPENAI_API_KEY"]


def test_provider_auth_reports_configured_api_key(monkeypatch, tmp_path):
    db_path = tmp_path / "provider-api.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))
    monkeypatch.setenv("HEYGENT_OPENAI_API_KEY", "sk-test")

    with TestClient(app) as local_client:
        auth_response = local_client.post("/ai/api/v1/providers/openai_api/auth", json={"force_oauth": False})
        provider_response = local_client.get("/ai/api/v1/providers/openai_api")

    assert auth_response.status_code == 200
    assert auth_response.json()["status"] == "connected"
    assert provider_response.json()["configured"] is True
    assert provider_response.json()["connected"] is True


def test_provider_callback_is_not_supported(client):
    response = client.post("/ai/api/v1/providers/openai_api/callback", json={"code": "code-123", "state": "state-123"})

    assert response.status_code == 200
    assert response.json()["status"] == "not_supported"


def test_provider_refresh_reports_api_key_status(client):
    response = client.post("/ai/api/v1/providers/openai_api/refresh")

    assert response.status_code == 200
    assert response.json()["status"] in {"connected", "configuration_required"}


def test_provider_disconnect_is_env_managed(client):
    response = client.post("/ai/api/v1/providers/openai_api/disconnect")

    assert response.status_code == 200
    assert response.json()["status"] == "env_managed"
