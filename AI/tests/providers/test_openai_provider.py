import httpx

from app.core.config import Settings
from app.domain.providers.openai_oauth import OpenAIOAuthProvider
from app.domain.providers.registry import ProviderRegistry
from app.storage.sqlite import SQLiteTaskRepository


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


def test_openai_provider_health_and_stub_generate(tmp_path):
    repository = SQLiteTaskRepository(tmp_path / "provider.db")
    provider = OpenAIOAuthProvider(Settings(), repository)

    health = provider.health()
    generated = provider.generate("hello backbone")

    assert health.provider_name == "openai_oauth"
    assert health.healthy is True
    assert health.connected is False
    assert generated.output_text.startswith("[stub:openai_oauth]")


def test_openai_provider_completes_auth_and_generates_live(monkeypatch, tmp_path):
    repository = SQLiteTaskRepository(tmp_path / "provider-live.db")
    settings = Settings(
        openai_oauth_client_id="client-id",
        openai_oauth_client_secret="client-secret",
        openai_oauth_redirect_uri="http://127.0.0.1:8000/api/v1/providers/openai_oauth/callback",
        openai_oauth_authorize_url="https://auth.openai.test/authorize",
        openai_oauth_token_url="https://auth.openai.test/token",
        openai_oauth_scopes=["model.generate"],
        openai_api_base_url="https://api.openai.test/v1",
        openai_response_model="gpt-test",
    )
    provider = OpenAIOAuthProvider(settings, repository)
    auth = provider.start_auth()

    def fake_post(url, data=None, headers=None, timeout=None, json=None):
        if url == settings.openai_oauth_token_url:
            return DummyHTTPResponse(
                {
                    "access_token": "live-token",
                    "refresh_token": "refresh-token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "scope": "model.generate",
                }
            )
        if url == f"{settings.openai_api_base_url}/responses":
            return DummyHTTPResponse(
                {
                    "id": "resp_123",
                    "model": settings.openai_response_model,
                    "output_text": "실제 연결 응답",
                    "usage": {"input_tokens": 4, "output_tokens": 3},
                }
            )
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr("app.domain.providers.openai_oauth.httpx.post", fake_post)
    connected = provider.complete_auth(code="code-123", state=auth.state)
    generated = provider.generate("연결 확인")

    assert connected.connected is True
    assert provider.health().connected is True
    assert generated.output_text == "실제 연결 응답"
    assert generated.metadata["mode"] == "live"


def test_openai_provider_refresh_and_disconnect(monkeypatch, tmp_path):
    repository = SQLiteTaskRepository(tmp_path / "provider-refresh.db")
    settings = Settings(
        openai_oauth_client_id="client-id",
        openai_oauth_client_secret="client-secret",
        openai_oauth_redirect_uri="http://127.0.0.1:8000/api/v1/providers/openai_oauth/callback",
        openai_oauth_authorize_url="https://auth.openai.test/authorize",
        openai_oauth_token_url="https://auth.openai.test/token",
        openai_oauth_scopes=["model.generate"],
    )
    provider = OpenAIOAuthProvider(settings, repository)
    repository.upsert_provider_token(
        "openai_oauth",
        {
            "access_token": "old-token",
            "refresh_token": "refresh-token",
            "token_type": "Bearer",
            "scope_text": "model.generate",
            "expires_at": None,
            "raw_payload": {"ok": True},
        },
    )

    def fake_post(url, data=None, headers=None, timeout=None, json=None):
        if url == settings.openai_oauth_token_url:
            return DummyHTTPResponse(
                {
                    "access_token": "new-token",
                    "refresh_token": "new-refresh-token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "scope": "model.generate",
                }
            )
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr("app.domain.providers.openai_oauth.httpx.post", fake_post)
    refreshed = provider.refresh_connection()
    disconnected = provider.disconnect()

    assert refreshed.status == "refreshed"
    assert refreshed.connected is True
    assert disconnected.status == "disconnected"
    assert provider.health().connected is False


def test_provider_registry_returns_health_list(tmp_path):
    repository = SQLiteTaskRepository(tmp_path / "registry.db")
    registry = ProviderRegistry([OpenAIOAuthProvider(Settings(), repository)])

    names = registry.list_names()
    health_list = registry.health()

    assert names == ["openai_oauth"]
    assert health_list[0].provider_name == "openai_oauth"
