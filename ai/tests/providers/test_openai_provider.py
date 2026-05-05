import base64
import httpx
import json

from app.core.config import Settings
from app.domain.providers.model import OpenAIOAuthProvider
from app.domain.providers.model.openai_api import OpenAIAPIProvider
from app.domain.providers.registry import ProviderRegistry
from tests.fakes import InMemoryTaskRepository


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
        json.dumps({"exp": 4102444800, "scp": ["agent.loop"], "https://api.openai.com/auth": {"chatgpt_account_id": "acct_test"}}).encode()
    ).decode().rstrip("=")
    return f"{header}.{payload}.sig"


def test_openai_provider_health_and_stub_respond():
    repository = InMemoryTaskRepository()
    provider = OpenAIOAuthProvider(Settings(), repository)

    health = provider.health()
    response = provider.respond(messages=[{"role": "user", "content": "hello backbone"}], tools=[], model="gpt-test")

    assert health.provider_name == "openai_oauth"
    assert health.healthy is True
    assert health.configured is True
    assert health.connected is False
    assert response.output_text.startswith("[stub:openai_oauth]")


def test_openai_provider_imports_local_codex_auth_and_responds_live(monkeypatch, tmp_path):
    repository = InMemoryTaskRepository()
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

    monkeypatch.setattr("app.domain.providers.model.openai_oauth.httpx.stream", fake_stream)
    auth = provider.start_auth(force_oauth=False)
    response = provider.respond(messages=[{"role": "user", "content": "연결 확인"}], tools=[], model="gpt-test")

    assert auth.status == "connected"
    assert provider.health().configured is True
    assert provider.health().connected is True
    assert response.output_text == "로컬 로그인 연결 응답"
    assert response.metadata["mode"] == "live"


def test_openai_api_provider_respond_preserves_native_tool_call(monkeypatch):
    settings = Settings(
        openai_api_key="sk-test",
        openai_rest_api_base_url="https://api.openai.test/v1",
        openai_response_model="gpt-fallback",
    )
    provider = OpenAIAPIProvider(settings)
    captured: dict = {}

    def fake_post(url, headers=None, json=None, timeout=None, data=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return DummyHTTPResponse(
            {
                "id": "resp_tool",
                "model": "gpt-agent",
                "status": "completed",
                "metadata": {"trace": "abc"},
                "output": [
                    {
                        "type": "reasoning",
                        "summary": [{"text": "도구가 필요함"}],
                        "encrypted_content": "reasoning-token",
                    },
                    {
                        "type": "function_call",
                        "call_id": "call_todo_1",
                        "name": "todo",
                        "arguments": '{"todos":[{"content":"정리","status":"pending"}]}',
                    },
                ],
                "usage": {"input_tokens": 12, "output_tokens": 4},
            }
        )

    monkeypatch.setattr("app.domain.providers.model.openai_api.httpx.post", fake_post)

    response = provider.respond(
        messages=[
            {"role": "user", "content": "할 일을 정리해줘"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_previous",
                        "name": "todo",
                        "arguments": '{"todos":[]}',
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "call_previous", "content": '{"todos":[]}'},
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "todo",
                    "description": "todo list 관리",
                    "parameters": {"type": "object", "properties": {"todos": {"type": "array"}}},
                    "strict": True,
                },
            }
        ],
        model="gpt-agent",
        tool_choice="auto",
    )

    assert captured["url"] == "https://api.openai.test/v1/responses"
    assert captured["json"]["model"] == "gpt-agent"
    assert captured["json"]["input"] == [
        {"role": "user", "content": "할 일을 정리해줘"},
        {"type": "function_call", "call_id": "call_previous", "name": "todo", "arguments": '{"todos":[]}'},
        {"type": "function_call_output", "call_id": "call_previous", "output": '{"todos":[]}'},
    ]
    assert captured["json"]["tools"][0]["name"] == "todo"
    assert captured["json"]["tools"][0]["strict"] is True
    assert captured["json"]["tool_choice"] == "auto"
    assert response.finish_reason == "tool_calls"
    assert response.tool_calls[0].id == "call_todo_1"
    assert response.tool_calls[0].name == "todo"
    assert response.tool_calls[0].arguments["todos"][0]["content"] == "정리"
    assert response.reasoning[0]["encrypted_content"] == "reasoning-token"
    assert response.raw_response["id"] == "resp_tool"
    assert response.metadata["response_id"] == "resp_tool"
    assert response.metadata["raw_metadata"] == {"trace": "abc"}


def test_openai_oauth_provider_respond_streams_agent_contract(monkeypatch, tmp_path):
    repository = InMemoryTaskRepository()
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
    captured: dict = {}

    def fake_stream(method, url, headers=None, json=None, timeout=None):
        captured["method"] = method
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return DummyStreamResponse(
            [
                'data: {"type":"response.completed","response":{"id":"resp_oauth_tool","model":"gpt-test","status":"completed","output":[{"type":"function_call","call_id":"call_1","name":"todo","arguments":"{\\"todos\\":[]}"}],"usage":{"input_tokens":5,"output_tokens":2}}}',
            ],
            url=url,
        )

    monkeypatch.setattr("app.domain.providers.model.openai_oauth.httpx.stream", fake_stream)

    auth = provider.start_auth(force_oauth=False)
    response = provider.respond(
        messages=[
            {"role": "user", "content": "todo를 읽어줘"},
            {"role": "tool", "tool_call_id": "call_previous", "content": '{"todos":[]}'},
        ],
        tools=[{"type": "function", "name": "todo", "description": "todo list 관리", "parameters": {"type": "object"}}],
        model="gpt-test",
    )

    assert auth.status == "connected"
    assert captured["method"] == "POST"
    assert captured["url"] == f"{settings.openai_api_base_url}/codex/responses"
    assert captured["json"]["stream"] is True
    assert captured["json"]["input"][1] == {
        "type": "function_call_output",
        "call_id": "call_previous",
        "output": '{"todos":[]}',
    }
    assert response.finish_reason == "tool_calls"
    assert response.tool_calls[0].id == "call_1"
    assert response.tool_calls[0].name == "todo"
    assert response.raw_response["id"] == "resp_oauth_tool"


def test_openai_provider_completes_auth_and_responds_live(monkeypatch):
    repository = InMemoryTaskRepository()
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

    monkeypatch.setattr("app.domain.providers.model.openai_oauth.httpx.post", fake_post)
    monkeypatch.setattr("app.domain.providers.model.openai_oauth.httpx.stream", fake_stream)
    connected = provider.complete_auth(code="code-123", state=auth.state)
    response = provider.respond(messages=[{"role": "user", "content": "연결 확인"}], tools=[], model="gpt-test")

    assert connected.connected is True
    assert provider.health().connected is True
    assert response.output_text == "실제 연결 응답"
    assert response.metadata["mode"] == "live"


def test_openai_provider_refresh_and_disconnect(monkeypatch):
    repository = InMemoryTaskRepository()
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
            "scope_text": "agent.loop",
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

    monkeypatch.setattr("app.domain.providers.model.openai_oauth.httpx.post", fake_post)
    refreshed = provider.refresh_connection()
    disconnected = provider.disconnect()

    assert refreshed.status == "refreshed"
    assert refreshed.connected is True
    assert disconnected.status == "disconnected"
    assert provider.health().connected is False


def test_provider_registry_returns_health_list():
    repository = InMemoryTaskRepository()
    registry = ProviderRegistry([OpenAIOAuthProvider(Settings(), repository)])

    names = registry.list_names()
    health_list = registry.health()

    assert names == ["openai_oauth"]
    assert health_list[0].provider_name == "openai_oauth"
