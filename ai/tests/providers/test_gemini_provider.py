import httpx
import pytest

from app.core.config import Settings
from app.domain.providers.model.gemini_api import GeminiAPIProvider
from app.domain.providers.registry import ProviderRegistry


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
            raise httpx.HTTPStatusError(
                "error",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request, text=self.text),
            )


@pytest.mark.asyncio
async def test_gemini_api_provider_uses_backend_credential_and_records_usage_async():
    settings = Settings(agent_model_request_timeout_seconds=9)
    issued: list[dict] = []
    recorded: list[dict] = []
    captured: dict = {}

    class FakeBackendAiClient:
        async def issue_credential(self, **kwargs):
            issued.append(kwargs)

            class Credential:
                provider_name = "gemini_api_key"
                model = "gemini-2.5-pro"
                credential_type = "api_key"
                credential = "gemini-issued"

            return Credential()

        async def record_command_usage(self, **kwargs):
            recorded.append(kwargs)

    class FakeGeminiHttpClient:
        async def post(self, url, params=None, json=None, timeout=None):
            captured["url"] = url
            captured["params"] = params
            captured["json"] = json
            captured["timeout"] = timeout
            return DummyHTTPResponse(
                {
                    "responseId": "gemini-response-1",
                    "candidates": [
                        {
                            "finishReason": "STOP",
                            "content": {
                                "role": "model",
                                "parts": [{"text": "Gemini 응답"}],
                            },
                        }
                    ],
                    "usageMetadata": {
                        "promptTokenCount": 7,
                        "candidatesTokenCount": 3,
                        "totalTokenCount": 10,
                    },
                }
            )

    provider = GeminiAPIProvider(
        settings,
        http_client=FakeGeminiHttpClient(),
        backend_ai_client=FakeBackendAiClient(),
    )

    response = await provider.respond_async(
        messages=[{"role": "user", "content": "hello"}],
        tools=[],
        model="gemini-2.5-pro",
        runtime_context={
            "user_id": "10",
            "provider_name": "gemini_api_key",
            "task_run_id": "task-1",
            "step_run_id": "step-1",
            "session_id": "session-1",
        },
    )

    assert issued == [{"user_id": "10", "provider_name": "gemini_api_key", "model": "gemini-2.5-pro"}]
    assert captured["url"] == "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent"
    assert captured["params"] == {"key": "gemini-issued"}
    assert captured["json"]["contents"] == [{"role": "user", "parts": [{"text": "hello"}]}]
    assert captured["timeout"] == 9
    assert recorded == [
        {
            "user_id": "10",
            "provider_name": "gemini_api_key",
            "model": "gemini-2.5-pro",
            "task_run_id": "task-1",
            "step_run_id": "step-1",
            "session_id": "session-1",
            "request_id": "gemini-response-1",
            "usage": {"input_tokens": 7, "output_tokens": 3, "total_tokens": 10},
            "metadata": {
                "command": "agent_loop",
                "provider": "gemini_api",
                "response_id": "gemini-response-1",
            },
        }
    ]
    assert response.provider_name == "gemini_api_key"
    assert response.output_text == "Gemini 응답"


@pytest.mark.asyncio
async def test_gemini_api_provider_preserves_function_call_async():
    settings = Settings()
    captured: dict = {}

    class FakeBackendAiClient:
        async def issue_credential(self, **kwargs):
            class Credential:
                provider_name = "gemini_api_key"
                model = "gemini-2.5-flash"
                credential_type = "api_key"
                credential = "gemini-issued"

            return Credential()

        async def record_command_usage(self, **kwargs):
            raise AssertionError("usage should not be recorded without task_run_id")

    class FakeGeminiHttpClient:
        async def post(self, url, params=None, json=None, timeout=None):
            captured["json"] = json
            return DummyHTTPResponse(
                {
                    "candidates": [
                        {
                            "finishReason": "FUNCTION_CALL",
                            "content": {
                                "parts": [
                                    {
                                        "functionCall": {
                                            "name": "todo",
                                            "args": {"todos": [{"content": "정리", "status": "pending"}]},
                                        }
                                    }
                                ]
                            },
                        }
                    ]
                }
            )

    provider = GeminiAPIProvider(
        settings,
        http_client=FakeGeminiHttpClient(),
        backend_ai_client=FakeBackendAiClient(),
    )

    response = await provider.respond_async(
        messages=[{"role": "user", "content": "할 일을 정리해줘"}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "todo",
                    "description": "todo list 관리",
                    "parameters": {"type": "object", "properties": {"todos": {"type": "array"}}},
                },
            }
        ],
        model="gemini-2.5-flash",
        runtime_context={"user_id": "10", "provider_name": "gemini_api_key"},
    )

    assert captured["json"]["tools"][0]["functionDeclarations"][0]["name"] == "todo"
    assert response.finish_reason == "function_call"
    assert response.tool_calls[0].name == "todo"
    assert response.tool_calls[0].arguments["todos"][0]["content"] == "정리"


def test_provider_registry_maps_gemini_backend_provider_to_gemini_runtime_provider():
    settings = Settings()
    registry = ProviderRegistry([GeminiAPIProvider(settings)])

    provider = registry.model_provider_for("gemini_api_key")

    assert provider.name == "gemini_api"
