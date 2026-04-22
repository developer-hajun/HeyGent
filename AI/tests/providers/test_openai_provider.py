import base64
import httpx
import json

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


class DummyStreamResponse:
    def __init__(self, lines: list[str], status_code: int = 200, url: str = "https://example.test"):
        self._lines = lines
        self.status_code = status_code
        self.is_success = status_code < 400
        self.reason_phrase = "OK" if self.is_success else "Bad Request"
        self.request = httpx.Request("POST", url)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def iter_lines(self):
        for line in self._lines:
            yield line

    def read(self):
        return "\n".join(self._lines).encode("utf-8")


def _make_test_access_token() -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none"}).encode()).decode().rstrip("=")
    payload = base64.urlsafe_b64encode(
        json.dumps({"exp": 4102444800, "scp": ["model.generate"], "https://api.openai.com/auth": {"chatgpt_account_id": "acct_test"}}).encode()
    ).decode().rstrip("=")
    return f"{header}.{payload}.sig"


def test_openai_provider_health_and_stub_generate(tmp_path):
    repository = SQLiteTaskRepository(tmp_path / "provider.db")
    provider = OpenAIOAuthProvider(Settings(), repository)

    health = provider.health()
    generated = provider.generate("hello backbone")

    assert health.provider_name == "openai_oauth"
    assert health.healthy is True
    assert health.configured is True
    assert health.connected is False
    assert generated.output_text.startswith("[stub:openai_oauth]")


def test_openai_provider_imports_local_codex_auth_and_generates_live(monkeypatch, tmp_path):
    repository = SQLiteTaskRepository(tmp_path / "provider-codex.db")
    auth_path = tmp_path / "auth.json"
    auth_path.write_text(
        json.dumps(
            {
                "auth_mode": "chatgpt",
                "tokens": {
                    "access_token": _make_test_access_token(),
                    "refresh_token": "refresh-token",
                    "account_id": "acct_test",
                },
            }
        ),
        encoding="utf-8",
    )
    settings = Settings(
        openai_auth_file=auth_path,
        openai_api_base_url="https://chatgpt.test/backend-api",
        openai_response_model="gpt-test",
    )
    provider = OpenAIOAuthProvider(settings, repository)

    def fake_stream(method, url, headers=None, json=None, timeout=None):
        if method == "POST" and url == f"{settings.openai_api_base_url}/codex/responses":
            return DummyStreamResponse(
                [
                    'data: {"type":"response.output_text.delta","delta":"로컬 로그인 연결 응답"}',
                    'data: {"type":"response.completed","response":{"id":"resp_codex","model":"gpt-test","usage":{"input_tokens":3,"output_tokens":3}}}',
                ],
                url=url,
            )
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr("app.domain.providers.openai_oauth.httpx.stream", fake_stream)
    auth = provider.start_auth(force_oauth=False)
    generated = provider.generate("연결 확인")

    assert auth.status == "connected"
    assert provider.health().configured is True
    assert provider.health().connected is True
    assert generated.output_text == "로컬 로그인 연결 응답"
    assert generated.metadata["mode"] == "live"


def test_openai_provider_completes_auth_and_generates_live(monkeypatch, tmp_path):
    repository = SQLiteTaskRepository(tmp_path / "provider-live.db")
    settings = Settings(
        openai_oauth_client_id="client-id",
        openai_oauth_redirect_uri="http://localhost:1455/auth/callback",
        openai_oauth_authorize_url="https://auth.openai.test/authorize",
        openai_oauth_token_url="https://auth.openai.test/token",
        openai_oauth_scopes=["openid", "profile", "email", "offline_access"],
        openai_api_base_url="https://chatgpt.test/backend-api",
        openai_response_model="gpt-test",
    )
    provider = OpenAIOAuthProvider(settings, repository)
    auth = provider.start_auth(force_oauth=True)

    def fake_post(url, data=None, headers=None, timeout=None, json=None):
        if url == settings.openai_oauth_token_url:
            return DummyHTTPResponse(
                {
                    "access_token": _make_test_access_token(),
                    "refresh_token": "refresh-token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "scope": "openid profile email offline_access",
                }
            )
        raise AssertionError(f"unexpected url: {url}")

    def fake_stream(method, url, headers=None, json=None, timeout=None):
        if method == "POST" and url == f"{settings.openai_api_base_url}/codex/responses":
            return DummyStreamResponse(
                [
                    'data: {"type":"response.output_text.delta","delta":"실제 연결 응답"}',
                    'data: {"type":"response.completed","response":{"id":"resp_123","model":"gpt-test","usage":{"input_tokens":4,"output_tokens":3}}}',
                ],
                url=url,
            )
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr("app.domain.providers.openai_oauth.httpx.post", fake_post)
    monkeypatch.setattr("app.domain.providers.openai_oauth.httpx.stream", fake_stream)
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
        openai_oauth_redirect_uri="http://localhost:1455/auth/callback",
        openai_oauth_authorize_url="https://auth.openai.test/authorize",
        openai_oauth_token_url="https://auth.openai.test/token",
        openai_oauth_scopes=["openid", "profile", "email", "offline_access"],
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
                    "access_token": _make_test_access_token(),
                    "refresh_token": "new-refresh-token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "scope": "openid profile email offline_access",
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
