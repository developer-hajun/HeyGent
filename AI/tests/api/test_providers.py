import httpx
from fastapi.testclient import TestClient

from app.main import app


class DummyHTTPResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)
        self.request = httpx.Request("POST", "https://example.test")

    def json(self):
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=self.request, response=httpx.Response(self.status_code, request=self.request, text=self.text))


def test_list_providers(client):
    response = client.get("/api/v1/providers")

    assert response.status_code == 200
    assert response.json()[0]["provider_name"] == "openai_oauth"
    assert response.json()[0]["configured"] is False


def test_get_provider_detail(client):
    response = client.get("/api/v1/providers/openai_oauth")

    assert response.status_code == 200
    body = response.json()
    assert body["provider_name"] == "openai_oauth"
    assert "HEYGENT_OPENAI_OAUTH_CLIENT_ID" in body["missing_env"]


def test_provider_auth_start_returns_missing_env(client):
    response = client.post("/api/v1/providers/openai_oauth/auth", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "configuration_required"
    assert "HEYGENT_OPENAI_OAUTH_CLIENT_SECRET" in body["missing_env"]


def test_provider_callback_connects_provider(monkeypatch, tmp_path):
    db_path = tmp_path / "provider-api.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))
    monkeypatch.setenv("HEYGENT_OPENAI_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setenv("HEYGENT_OPENAI_OAUTH_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("HEYGENT_OPENAI_OAUTH_REDIRECT_URI", "http://127.0.0.1:8000/api/v1/providers/openai_oauth/callback")
    monkeypatch.setenv("HEYGENT_OPENAI_OAUTH_AUTHORIZE_URL", "https://auth.openai.test/authorize")
    monkeypatch.setenv("HEYGENT_OPENAI_OAUTH_TOKEN_URL", "https://auth.openai.test/token")
    monkeypatch.setenv("HEYGENT_OPENAI_OAUTH_SCOPES", "model.generate")

    def fake_post(url, data=None, headers=None, timeout=None, json=None):
        if url == "https://auth.openai.test/token":
            return DummyHTTPResponse(
                {
                    "access_token": "token-123",
                    "refresh_token": "refresh-123",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "scope": "model.generate",
                }
            )
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr("app.domain.providers.openai_oauth.httpx.post", fake_post)

    with TestClient(app) as local_client:
        auth_response = local_client.post("/api/v1/providers/openai_oauth/auth", json={})
        state = auth_response.json()["state"]

        callback_response = local_client.post(
            "/api/v1/providers/openai_oauth/callback",
            json={"code": "code-123", "state": state},
        )
        provider_response = local_client.get("/api/v1/providers/openai_oauth")

    assert callback_response.status_code == 200
    assert callback_response.json()["connected"] is True
    assert provider_response.json()["connected"] is True


def test_provider_generate(client):
    response = client.post(
        "/api/v1/providers/generate",
        json={"provider_name": "openai_oauth", "prompt": "summarize this", "metadata": {"temperature": 0}},
    )

    assert response.status_code == 200
    assert response.json()["output_text"].startswith("[stub:openai_oauth]")
