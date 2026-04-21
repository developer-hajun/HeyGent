import base64
import httpx
import json
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


def _make_test_access_token() -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none"}).encode()).decode().rstrip("=")
    payload = base64.urlsafe_b64encode(
        json.dumps({"exp": 4102444800, "scp": ["model.generate"], "https://api.openai.com/auth": {"chatgpt_account_id": "acct_test"}}).encode()
    ).decode().rstrip("=")
    return f"{header}.{payload}.sig"


def test_list_providers(client):
    response = client.get("/api/v1/providers")

    assert response.status_code == 200
    assert response.json()[0]["provider_name"] == "openai_oauth"
    assert response.json()[0]["configured"] is True


def test_get_provider_detail(client):
    response = client.get("/api/v1/providers/openai_oauth")

    assert response.status_code == 200
    body = response.json()
    assert body["provider_name"] == "openai_oauth"
    assert body["missing_env"] == []


def test_provider_auth_start_returns_authorization_url(client):
    response = client.post("/api/v1/providers/openai_oauth/auth", json={"force_oauth": True})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "authorization_required"
    assert body["authorization_url"].startswith("https://auth.openai.com/oauth/authorize?")
    assert body["redirect_uri"] == "http://127.0.0.1:8000/api/v1/providers/openai_oauth/callback"


def test_provider_auth_start_imports_local_chatgpt_login(monkeypatch, tmp_path):
    db_path = tmp_path / "provider-local-auth.db"
    auth_path = tmp_path / "auth.json"
    auth_path.write_text(
        json.dumps(
            {
                "auth_mode": "chatgpt",
                "tokens": {
                    "access_token": _make_test_access_token(),
                    "refresh_token": "refresh-123",
                    "account_id": "acct_test",
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))
    monkeypatch.setenv("HEYGENT_OPENAI_AUTH_FILE", str(auth_path))

    with TestClient(app) as local_client:
        auth_response = local_client.post("/api/v1/providers/openai_oauth/auth", json={"force_oauth": False})
        provider_response = local_client.get("/api/v1/providers/openai_oauth")

    assert auth_response.status_code == 200
    assert auth_response.json()["status"] == "connected"
    assert provider_response.json()["configured"] is True
    assert provider_response.json()["connected"] is True


def test_provider_callback_connects_provider(monkeypatch, tmp_path):
    db_path = tmp_path / "provider-api.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))
    monkeypatch.setenv("HEYGENT_OPENAI_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setenv("HEYGENT_OPENAI_OAUTH_REDIRECT_URI", "http://127.0.0.1:8000/api/v1/providers/openai_oauth/callback")
    monkeypatch.setenv("HEYGENT_OPENAI_OAUTH_AUTHORIZE_URL", "https://auth.openai.test/authorize")
    monkeypatch.setenv("HEYGENT_OPENAI_OAUTH_TOKEN_URL", "https://auth.openai.test/token")
    monkeypatch.setenv("HEYGENT_OPENAI_OAUTH_SCOPES", "openid,profile,email,offline_access")

    def fake_post(url, data=None, headers=None, timeout=None, json=None):
        if url == "https://auth.openai.test/token":
            return DummyHTTPResponse(
                {
                    "access_token": _make_test_access_token(),
                    "refresh_token": "refresh-123",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "scope": "openid profile email offline_access",
                }
            )
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr("app.domain.providers.openai_oauth.httpx.post", fake_post)

    with TestClient(app) as local_client:
        auth_response = local_client.post("/api/v1/providers/openai_oauth/auth", json={"force_oauth": True})
        state = auth_response.json()["state"]

        callback_response = local_client.post(
            "/api/v1/providers/openai_oauth/callback",
            json={"code": "code-123", "state": state},
        )
        provider_response = local_client.get("/api/v1/providers/openai_oauth")

    assert callback_response.status_code == 200
    assert callback_response.json()["connected"] is True
    assert provider_response.json()["connected"] is True


def test_provider_refresh_requires_connection(client):
    response = client.post("/api/v1/providers/openai_oauth/refresh")

    assert response.status_code == 200
    assert response.json()["status"] in {"reconnect_required", "not_connected"}


def test_provider_disconnect_clears_connection(monkeypatch, tmp_path):
    db_path = tmp_path / "provider-disconnect.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))
    monkeypatch.setenv("HEYGENT_OPENAI_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setenv("HEYGENT_OPENAI_OAUTH_REDIRECT_URI", "http://127.0.0.1:8000/api/v1/providers/openai_oauth/callback")
    monkeypatch.setenv("HEYGENT_OPENAI_OAUTH_AUTHORIZE_URL", "https://auth.openai.test/authorize")
    monkeypatch.setenv("HEYGENT_OPENAI_OAUTH_TOKEN_URL", "https://auth.openai.test/token")
    monkeypatch.setenv("HEYGENT_OPENAI_OAUTH_SCOPES", "openid,profile,email,offline_access")

    def fake_post(url, data=None, headers=None, timeout=None, json=None):
        if url == "https://auth.openai.test/token":
            return DummyHTTPResponse(
                {
                    "access_token": _make_test_access_token(),
                    "refresh_token": "refresh-123",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "scope": "openid profile email offline_access",
                }
            )
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr("app.domain.providers.openai_oauth.httpx.post", fake_post)

    with TestClient(app) as local_client:
        auth_response = local_client.post("/api/v1/providers/openai_oauth/auth", json={"force_oauth": True})
        state = auth_response.json()["state"]
        local_client.post("/api/v1/providers/openai_oauth/callback", json={"code": "code-123", "state": state})

        disconnect_response = local_client.post("/api/v1/providers/openai_oauth/disconnect")
        provider_response = local_client.get("/api/v1/providers/openai_oauth")

    assert disconnect_response.status_code == 200
    assert disconnect_response.json()["status"] == "disconnected"
    assert provider_response.json()["connected"] is False


def test_provider_generate(client):
    response = client.post(
        "/api/v1/providers/generate",
        json={"provider_name": "openai_oauth", "prompt": "summarize this", "metadata": {"temperature": 0}},
    )

    assert response.status_code == 200
    assert response.json()["output_text"].startswith("[stub:openai_oauth]")
