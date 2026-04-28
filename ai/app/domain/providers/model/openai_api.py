from __future__ import annotations
from typing import Any

import httpx

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


class OpenAIAPIProvider(BaseProvider):
    """API key 기반 OpenAI Responses provider 다."""

    name = "openai_api"
    auth_type = "api_key"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

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
    ) -> AgentModelResponse:
        requested_model = str(model or self.settings.openai_response_model).strip() or self.settings.openai_response_model
        if not self.settings.openai_api_key:
            return self._stub_agent_response(messages=messages, model=requested_model)

        request_body = self._build_responses_request_body(
            messages=messages,
            tools=tools,
            model=requested_model,
            tool_choice=tool_choice,
        )
        response = httpx.post(
            f"{self.settings.openai_rest_api_base_url.rstrip('/')}/responses",
            headers={
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json=request_body,
            timeout=60.0,
        )
        response.raise_for_status()
        return build_agent_model_response(
            provider_name=self.name,
            requested_model=requested_model,
            response_json=response.json(),
            metadata={
                "mode": "live",
                "auth_type": self.auth_type,
                "connected": True,
                "tool_choice": tool_choice,
            },
        )

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
