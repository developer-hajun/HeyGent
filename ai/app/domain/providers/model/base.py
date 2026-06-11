from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
import inspect
import json
from typing import Any, Literal

from pydantic import Field

from app.contracts.common.base import ContractModel
from app.contracts.provider.provider_response import ProviderAuthResponse, ProviderConnectionResponse, ProviderHealthResponse


AgentRole = Literal["system", "developer", "user", "assistant", "tool"]


class AssistantToolCall(ContractModel):
    """assistant가 요청한 native tool call(모델이 구조화된 도구 호출을 직접 반환하는 방식)이다."""

    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    arguments_json: str | None = None
    type: str = "function"
    raw: dict[str, Any] = Field(default_factory=dict)


class AgentMessage(ContractModel):
    """agent.loop가 provider에 넘기는 내부 메시지 형식이다.

    provider별 원본 message 형식은 여기로 모은 뒤 adapter에서 다시 변환한다. 이렇게 해야
    agent.loop가 특정 provider의 tool call 표현에 묶이지 않는다.
    """

    role: AgentRole
    content: str | list[dict[str, Any]] | None = None
    tool_calls: list[AssistantToolCall] = Field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolResultMessage(AgentMessage):
    """runtime tool 실행 결과를 모델에게 다시 넘기는 메시지다.

    tool_call_id는 assistant가 보낸 호출 id와 같은 값이어야 모델이 도구 응답을 이어 붙일 수 있다.
    """

    role: Literal["tool"] = "tool"
    tool_call_id: str
    content: str


class AgentModelResponse(ContractModel):
    """agent.loop가 소비하는 표준 provider 응답이다.

    output_text는 사용자에게 보여 줄 텍스트이고, tool_calls는 실행해야 할 구조화된 호출 목록이다.
    둘이 동시에 올 수 있으므로 loop 종료 여부는 output_text가 아니라 tool_calls 유무로 판단한다.
    """

    provider_name: str
    model: str
    message: AgentMessage
    output_text: str = ""
    tool_calls: list[AssistantToolCall] = Field(default_factory=list)
    finish_reason: str | None = None
    reasoning: Any = None
    usage: dict[str, Any] = Field(default_factory=dict)
    raw_response: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    progress_update: dict[str, Any] | None = None
    work_disposition: dict[str, Any] | None = None
    visible_text: str | None = None


def coerce_agent_message(message: AgentMessage | ToolResultMessage | dict[str, Any]) -> AgentMessage:
    """dict로 들어온 transcript 항목을 agent.loop 내부 메시지 계약으로 정규화한다."""

    if isinstance(message, AgentMessage):
        return message
    if not isinstance(message, dict):
        raise TypeError(f"unsupported agent message type: {type(message)!r}")

    tool_calls = [coerce_assistant_tool_call(tool_call) for tool_call in message.get("tool_calls") or []]
    role = message.get("role")
    if role not in {"system", "developer", "user", "assistant", "tool"}:
        raise ValueError(f"unsupported message role: {role!r}")
    return AgentMessage(
        role=role,
        content=message.get("content"),
        tool_calls=tool_calls,
        tool_call_id=message.get("tool_call_id") or message.get("call_id"),
        name=message.get("name"),
        metadata=message.get("metadata") or {},
    )


def coerce_assistant_tool_call(tool_call: AssistantToolCall | dict[str, Any]) -> AssistantToolCall:
    """provider별 tool call 모양을 AssistantToolCall 하나로 맞춘다.

    arguments는 문자열 JSON이나 이미 파싱된 dict로 올 수 있다. 파싱에 실패한 원문은 버리지 않고
    _raw에 보존해 이후 도구 검증이나 실행 단계에서 처리하게 둔다.
    """

    if isinstance(tool_call, AssistantToolCall):
        return tool_call
    if not isinstance(tool_call, dict):
        raise TypeError(f"unsupported tool call type: {type(tool_call)!r}")

    function = tool_call.get("function") if isinstance(tool_call.get("function"), dict) else {}
    name = tool_call.get("name") or function.get("name")
    arguments_json = tool_call.get("arguments") or function.get("arguments")
    arguments: dict[str, Any] = {}
    if isinstance(arguments_json, dict):
        arguments = arguments_json
        arguments_json = json.dumps(arguments, ensure_ascii=False)
    elif isinstance(arguments_json, str) and arguments_json.strip():
        try:
            parsed = json.loads(arguments_json)
            arguments = parsed if isinstance(parsed, dict) else {"value": parsed}
        except json.JSONDecodeError:
            arguments = {"_raw": arguments_json}
    return AssistantToolCall(
        id=str(tool_call.get("id") or tool_call.get("call_id") or ""),
        name=str(name or ""),
        arguments=arguments,
        arguments_json=arguments_json if isinstance(arguments_json, str) else None,
        type=str(tool_call.get("type") or "function"),
        raw=tool_call,
    )


# OpenAI Responses API 전용 함수들은 openai_format.py로 분리되었습니다.
# 하위 호환성을 위해 여기서 re-export합니다.
from app.domain.providers.model.openai_format import (  # noqa: E402
    build_agent_model_response,
    extract_responses_output_text,
    extract_responses_reasoning,
    extract_responses_tool_calls,
    messages_to_responses_input,
    parse_assistant_response_contract,
    tools_to_responses_tools,
)

__all__ = [
    "AgentMessage",
    "AgentModelResponse",
    "AgentRole",
    "AssistantToolCall",
    "BaseProvider",
    "ToolResultMessage",
    "build_agent_model_response",
    "coerce_agent_message",
    "coerce_assistant_tool_call",
    "extract_responses_output_text",
    "extract_responses_reasoning",
    "extract_responses_tool_calls",
    "messages_to_responses_input",
    "parse_assistant_response_contract",
    "tools_to_responses_tools",
]


class BaseProvider(ABC):
    """모델 SDK 직접 의존을 숨기는 최소 Provider 인터페이스다."""

    name: str

    @abstractmethod
    def health(self) -> ProviderHealthResponse:
        """현재 프로바이더 사용 가능 여부를 반환한다."""

    @abstractmethod
    def start_auth(
        self,
        *,
        redirect_uri: str | None = None,
        state: str | None = None,
        force_oauth: bool = False,
    ) -> ProviderAuthResponse:
        """OAuth 시작에 필요한 메타데이터를 반환한다.

        현재 단계에서는 실제 callback 처리를 완성하지 않더라도,
        어떤 설정이 필요하고 어떤 authorization URL(사용자 인증 페이지 주소)로 이동해야 하는지는
        공통 인터페이스로 노출해 두는 것이 중요하다.
        """

    @abstractmethod
    def complete_auth(self, *, code: str, state: str) -> ProviderConnectionResponse:
        """OAuth callback 이후 토큰 교환과 저장을 수행한다."""

    @abstractmethod
    def refresh_connection(self) -> ProviderConnectionResponse:
        """저장된 refresh token(갱신용 토큰)으로 access token(호출용 토큰)을 갱신한다."""

    @abstractmethod
    def disconnect(self) -> ProviderConnectionResponse:
        """저장된 provider 연결 정보를 제거한다."""

    @abstractmethod
    def respond(
        self,
        messages: list[AgentMessage | ToolResultMessage | dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        model: str,
        tool_choice: dict[str, Any] | str | None = None,
        runtime_context: dict[str, Any] | None = None,
    ) -> AgentModelResponse:
        """agent.loop용 message/tool 기반 응답을 반환한다."""

    async def respond_async(
        self,
        messages: list[AgentMessage | ToolResultMessage | dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        model: str,
        tool_choice: dict[str, Any] | str | None = None,
        runtime_context: dict[str, Any] | None = None,
    ) -> AgentModelResponse:
        """비동기 실행 경로용 응답을 반환한다.

        기존 sync provider는 thread fallback으로 호환하고, event-loop bound provider는 native async로
        override한다.
        """

        kwargs: dict[str, Any] = {
            "messages": messages,
            "tools": tools,
            "model": model,
            "tool_choice": tool_choice,
        }
        if "runtime_context" in inspect.signature(self.respond).parameters:
            kwargs["runtime_context"] = runtime_context
        return await asyncio.to_thread(self.respond, **kwargs)
