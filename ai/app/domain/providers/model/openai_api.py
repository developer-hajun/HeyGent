from __future__ import annotations

import asyncio
import inspect
import json
import time
from typing import Any, Callable, Awaitable

import httpx

from app.clients.backend_ai import BackendAiClient, BackendAiClientError
from app.contracts.provider.provider_response import ProviderAuthResponse, ProviderConnectionResponse, ProviderHealthResponse
from app.core.config import Settings
from app.domain.providers.model.base import (
    AgentMessage,
    AgentModelResponse,
    BaseProvider,
    ToolResultMessage,
    build_agent_model_response,
    messages_to_responses_input,
    tools_to_responses_tools,
)

# credential은 짧은 TTL로 캐싱해 LLM 턴마다 발생하는 auth HTTP 왕복을 제거한다.
_CREDENTIAL_CACHE_TTL = 170.0  # 초 (토큰 유효 시간보다 안전 마진 확보)
_credential_cache: dict[str, tuple[Any, float]] = {}
_credential_cache_lock = asyncio.Lock()


class OpenAIAPIProvider(BaseProvider):
    """API key 기반 OpenAI Responses provider 다."""

    name = "openai_api"
    auth_type = "api_key"

    def __init__(
        self,
        settings: Settings,
        *,
        http_client: httpx.AsyncClient | None = None,
        backend_ai_client: BackendAiClient | None = None,
    ) -> None:
        self.settings = settings
        self.backend_ai_client = backend_ai_client or BackendAiClient(settings=settings)
        self._http_client = http_client or httpx.AsyncClient()
        self._owns_http_client = http_client is None
        self._owns_backend_ai_client = backend_ai_client is None

    def health(self) -> ProviderHealthResponse:
        configured = bool(self.settings.openai_api_key)
        missing_env = [] if configured else ["HEYGENT_OPENAI_API_KEY"]
        detail = "환경 변수의 OpenAI API key 로 실제 OpenAI Responses 호출을 수행할 수 있습니다" if configured else "OpenAI API key 가 없어 REST provider 를 사용할 수 없습니다"
        return ProviderHealthResponse(
            provider_name=self.name,
            healthy=True,
            configured=configured,
            connected=configured,
            auth_type=self.auth_type,
            detail=detail,
            missing_env=missing_env,
            scopes=[],
            expires_at=None,
        )

    def start_auth(
        self,
        *,
        redirect_uri: str | None = None,
        state: str | None = None,
        force_oauth: bool = False,
    ) -> ProviderAuthResponse:
        configured = bool(self.settings.openai_api_key)
        return ProviderAuthResponse(
            provider_name=self.name,
            status="connected" if configured else "configuration_required",
            detail=(
                "OpenAI API key 가 설정되어 있어 바로 사용할 수 있습니다"
                if configured
                else "HEYGENT_OPENAI_API_KEY 를 설정하면 바로 사용할 수 있습니다"
            ),
            redirect_uri=redirect_uri,
            state=state,
            missing_env=[] if configured else ["HEYGENT_OPENAI_API_KEY"],
            metadata={"auth_type": self.auth_type},
        )

    def complete_auth(self, *, code: str, state: str) -> ProviderConnectionResponse:
        return ProviderConnectionResponse(
            provider_name=self.name,
            status="not_supported",
            connected=bool(self.settings.openai_api_key),
            detail="API key provider 는 OAuth callback 을 사용하지 않습니다",
        )

    def refresh_connection(self) -> ProviderConnectionResponse:
        configured = bool(self.settings.openai_api_key)
        return ProviderConnectionResponse(
            provider_name=self.name,
            status="connected" if configured else "configuration_required",
            connected=configured,
            detail=(
                "API key provider 는 별도 refresh 가 필요 없습니다"
                if configured
                else "HEYGENT_OPENAI_API_KEY 를 설정해야 합니다"
            ),
        )

    def disconnect(self) -> ProviderConnectionResponse:
        configured = bool(self.settings.openai_api_key)
        return ProviderConnectionResponse(
            provider_name=self.name,
            status="env_managed",
            connected=configured,
            detail="API key provider 는 .env 또는 환경 변수에서 관리됩니다. 연결 해제는 HEYGENT_OPENAI_API_KEY 제거로 처리합니다",
        )

    def respond(
        self,
        messages: list[AgentMessage | ToolResultMessage | dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        model: str,
        tool_choice: dict[str, Any] | str | None = None,
        runtime_context: dict[str, Any] | None = None,
    ) -> AgentModelResponse:
        requested_model = str(model or self.settings.openai_response_model).strip() or self.settings.openai_response_model
        credential_context = self._credential_context(runtime_context, requested_model)
        if credential_context is not None:
            raise RuntimeError("backend credential 기반 OpenAI API 호출은 respond_async를 사용해야 합니다")
        credential = None
        api_key = credential.credential if credential is not None else self.settings.openai_api_key
        if not api_key:
            return self._stub_agent_response(messages=messages, model=requested_model)
        call_provider_name = credential.provider_name if credential is not None else self.name
        call_model = credential.model if credential is not None else requested_model

        request_body = self._build_responses_request_body(
            messages=messages,
            tools=tools,
            model=call_model,
            tool_choice=tool_choice,
        )
        response = httpx.post(
            f"{self.settings.openai_rest_api_base_url.rstrip('/')}/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=request_body,
            timeout=self.settings.agent_model_request_timeout_seconds,
        )
        response.raise_for_status()
        agent_response = build_agent_model_response(
            provider_name=call_provider_name,
            requested_model=call_model,
            response_json=response.json(),
            metadata={
                "mode": "live",
                "auth_type": self.auth_type,
                "connected": True,
                "tool_choice": tool_choice,
            },
        )
        return agent_response

    async def respond_async(
        self,
        messages: list[AgentMessage | ToolResultMessage | dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        model: str,
        tool_choice: dict[str, Any] | str | None = None,
        runtime_context: dict[str, Any] | None = None,
        on_text_delta: Callable[[str], Awaitable[None]] | None = None,
    ) -> AgentModelResponse:
        """LLM 응답을 비동기로 요청한다.

        on_text_delta 콜백이 있으면 SSE 스트리밍으로 토큰을 실시간 전달하고,
        없으면 기존 단일 요청 방식으로 동작한다.
        """
        if type(self).respond is not OpenAIAPIProvider.respond:
            kwargs: dict[str, Any] = {
                "messages": messages,
                "tools": tools,
                "model": model,
                "tool_choice": tool_choice,
            }
            if "runtime_context" in inspect.signature(self.respond).parameters:
                kwargs["runtime_context"] = runtime_context
            return await asyncio.to_thread(self.respond, **kwargs)

        requested_model = str(model or self.settings.openai_response_model).strip() or self.settings.openai_response_model
        credential_context = self._credential_context(runtime_context, requested_model)
        credential = await self._issue_backend_credential_cached(credential_context) if credential_context is not None else None
        api_key = credential.credential if credential is not None else self.settings.openai_api_key
        if not api_key:
            return self._stub_agent_response(messages=messages, model=requested_model)
        call_provider_name = credential.provider_name if credential is not None else self.name
        call_model = credential.model if credential is not None else requested_model

        request_body = self._build_responses_request_body(
            messages=messages,
            tools=tools,
            model=call_model,
            tool_choice=tool_choice,
        )

        if on_text_delta is not None:
            agent_response = await self._respond_streaming(
                api_key=api_key,
                call_model=call_model,
                call_provider_name=call_provider_name,
                request_body=request_body,
                tool_choice=tool_choice,
                on_text_delta=on_text_delta,
            )
        else:
            response = await self._http_client.post(
                f"{self.settings.openai_rest_api_base_url.rstrip('/')}/responses",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=request_body,
                timeout=self.settings.agent_model_request_timeout_seconds,
            )
            response.raise_for_status()
            agent_response = build_agent_model_response(
                provider_name=call_provider_name,
                requested_model=call_model,
                response_json=response.json(),
                metadata={
                    "mode": "live",
                    "auth_type": self.auth_type,
                    "connected": True,
                    "tool_choice": tool_choice,
                },
            )

        if credential_context is not None:
            await self._record_backend_usage(
                credential_context=credential_context,
                model=agent_response.model,
                provider_name=call_provider_name,
                response=agent_response,
            )
        return agent_response

    async def _respond_streaming(
        self,
        *,
        api_key: str,
        call_model: str,
        call_provider_name: str,
        request_body: dict[str, Any],
        tool_choice: dict[str, Any] | str | None,
        on_text_delta: Callable[[str], Awaitable[None]],
    ) -> AgentModelResponse:
        """SSE 스트리밍으로 LLM 응답을 받고, 텍스트 델타를 즉시 콜백으로 전달한다.

        response.completed 이벤트에 완전한 응답 객체가 포함되므로
        이를 build_agent_model_response에 넘겨 기존 파싱 로직을 재사용한다.
        """
        stream_body = {**request_body, "stream": True}
        completed_response_json: dict[str, Any] | None = None
        accumulated_text_parts: list[str] = []

        async with self._http_client.stream(
            "POST",
            f"{self.settings.openai_rest_api_base_url.rstrip('/')}/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=stream_body,
            timeout=self.settings.agent_model_stream_timeout_seconds,
        ) as response:
            response.raise_for_status()
            async for raw_line in response.aiter_lines():
                line = raw_line.strip()
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    event_data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                event_type = event_data.get("type", "")

                if event_type == "response.output_text.delta":
                    delta = str(event_data.get("delta") or "")
                    if delta:
                        accumulated_text_parts.append(delta)
                        try:
                            await on_text_delta(delta)
                        except Exception:
                            pass

                elif event_type == "response.completed":
                    inner = event_data.get("response")
                    if isinstance(inner, dict):
                        completed_response_json = inner

        if completed_response_json is None:
            # 스트림이 response.completed 없이 끊긴 경우 빈 응답으로 처리한다.
            completed_response_json = {"id": "", "output": [], "usage": {}}

        # response.completed의 output에 텍스트가 없으면 누적한 delta 텍스트를 주입한다.
        # extract_responses_output_text가 output_text 직접 필드를 우선 참조하므로 여기에 삽입한다.
        if accumulated_text_parts and not self._has_text_in_output(completed_response_json):
            completed_response_json = {
                **completed_response_json,
                "output_text": "".join(accumulated_text_parts),
            }

        return build_agent_model_response(
            provider_name=call_provider_name,
            requested_model=call_model,
            response_json=completed_response_json,
            metadata={
                "mode": "live_stream",
                "auth_type": self.auth_type,
                "connected": True,
                "tool_choice": tool_choice,
            },
        )

    @staticmethod
    def _has_text_in_output(response_json: dict[str, Any]) -> bool:
        """response_json에 이미 추출 가능한 텍스트가 있는지 확인한다."""
        if isinstance(response_json.get("output_text"), str) and response_json["output_text"].strip():
            return True
        for item in response_json.get("output") or []:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "message" or item.get("role") == "assistant":
                return True
        return False

    async def aclose(self) -> None:
        if self._owns_http_client:
            await self._http_client.aclose()
        if self._owns_backend_ai_client:
            await self.backend_ai_client.aclose()

    async def list_user_models(self, *, user_id: str | int, model: str) -> list[str]:
        requested_model = str(model or self.settings.openai_response_model).strip() or self.settings.openai_response_model
        credential = await self.backend_ai_client.issue_credential(
            user_id=user_id,
            provider_name="openai_api_key",
            model=requested_model,
        )
        response = await self._http_client.get(
            f"{self.settings.openai_rest_api_base_url.rstrip('/')}/models",
            headers={"Authorization": f"Bearer {credential.credential}"},
            timeout=self.settings.agent_model_request_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            return []
        return sorted(
            {
                model_id
                for item in data
                if isinstance(item, dict)
                for model_id in [self._optional_text(item.get("id"))]
                if model_id and _is_openai_text_model(model_id)
            }
        )

    def _credential_context(self, runtime_context: dict[str, Any] | None, model: str) -> dict[str, str] | None:
        if not runtime_context:
            return None
        user_id = self._optional_text(runtime_context.get("user_id") or runtime_context.get("userId"))
        provider_name = self._optional_text(runtime_context.get("provider_name") or runtime_context.get("providerName"))
        task_run_id = self._optional_text(runtime_context.get("task_run_id") or runtime_context.get("taskRunId"))
        if not user_id or not provider_name or not task_run_id:
            return None
        return {
            "user_id": user_id,
            "provider_name": provider_name,
            "task_run_id": task_run_id,
            "step_run_id": self._optional_text(runtime_context.get("step_run_id") or runtime_context.get("stepRunId")) or "",
            "session_id": self._optional_text(runtime_context.get("session_id") or runtime_context.get("sessionId")) or "",
            "model": model,
        }

    async def _issue_backend_credential_cached(self, context: dict[str, str]):
        """backend credential을 TTL 캐시에서 반환해 LLM 턴마다 발생하는 HTTP 왕복을 제거한다."""
        cache_key = f"{context['user_id']}:{context['provider_name']}:{context['model']}"
        now = time.monotonic()

        async with _credential_cache_lock:
            cached = _credential_cache.get(cache_key)
            if cached is not None:
                credential, expires_at = cached
                if now < expires_at:
                    return credential

        try:
            credential = await self.backend_ai_client.issue_credential(
                user_id=context["user_id"],
                provider_name=context["provider_name"],
                model=context["model"],
            )
        except BackendAiClientError:
            raise

        async with _credential_cache_lock:
            _credential_cache[cache_key] = (credential, now + _CREDENTIAL_CACHE_TTL)

        return credential

    async def _issue_backend_credential(self, context: dict[str, str]):
        try:
            return await self.backend_ai_client.issue_credential(
                user_id=context["user_id"],
                provider_name=context["provider_name"],
                model=context["model"],
            )
        except BackendAiClientError:
            raise

    async def _record_backend_usage(
        self,
        *,
        credential_context: dict[str, str],
        model: str,
        provider_name: str,
        response: AgentModelResponse,
    ) -> None:
        try:
            await self.backend_ai_client.record_command_usage(
                user_id=credential_context["user_id"],
                provider_name=provider_name,
                model=model,
                task_run_id=credential_context["task_run_id"],
                step_run_id=credential_context["step_run_id"] or None,
                session_id=credential_context["session_id"] or None,
                request_id=self._optional_text(response.metadata.get("response_id")),
                usage=response.usage,
                metadata={
                    "command": "agent_loop",
                    "provider": self.name,
                    "response_id": self._optional_text(response.metadata.get("response_id")),
                },
            )
        except BackendAiClientError:
            return

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, int) and not isinstance(value, bool):
            return str(value)
        return None

    def _build_responses_request_body(
        self,
        *,
        messages: list[AgentMessage | ToolResultMessage | dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        model: str,
        tool_choice: dict[str, Any] | str | None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": model,
            "store": False,
            "input": messages_to_responses_input(messages),
        }
        normalized_tools = tools_to_responses_tools(tools)
        if normalized_tools:
            body["tools"] = normalized_tools
        if tool_choice is not None:
            body["tool_choice"] = tool_choice
        return body

    def _stub_agent_response(
        self,
        *,
        messages: list[AgentMessage | ToolResultMessage | dict[str, Any]],
        model: str,
    ) -> AgentModelResponse:
        preview = self._message_preview(messages)
        output_text = f"[stub:{self.name}] {preview}"
        message = AgentMessage(role="assistant", content=output_text)
        return AgentModelResponse(
            provider_name=self.name,
            model=model,
            message=message,
            output_text=output_text,
            finish_reason="stop",
            raw_response={"mode": "stub"},
            metadata={
                "mode": "stub",
                "auth_type": self.auth_type,
                "connected": False,
            },
        )

    @staticmethod
    def _message_preview(messages: list[AgentMessage | ToolResultMessage | dict[str, Any]]) -> str:
        for message in reversed(messages):
            content = message.content if isinstance(message, AgentMessage) else message.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()[:120]
        return ""


def _is_openai_text_model(model_id: str) -> bool:
    normalized = model_id.lower()
    if any(
        blocked in normalized
        for blocked in (
            "audio",
            "embedding",
            "image",
            "moderation",
            "realtime",
            "search",
            "sora",
            "transcribe",
            "tts",
            "whisper",
        )
    ):
        return False
    return normalized.startswith("gpt-") or normalized.startswith("o")
