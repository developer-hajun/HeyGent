"""OpenAI Responses API 전용 포맷 변환 함수 모음.

base.py에서 분리된 OpenAI Responses API 전용 헬퍼들이다.
openai_api.py는 이 모듈에서 import해서 사용한다.
"""
from __future__ import annotations

import json
import re
from typing import Any

from app.domain.providers.model.base import (
    AgentMessage,
    AgentModelResponse,
    AssistantToolCall,
    ToolResultMessage,
    coerce_agent_message,
    coerce_assistant_tool_call,
)


def messages_to_responses_input(messages: list[AgentMessage | ToolResultMessage | dict[str, Any]]) -> list[dict[str, Any]]:
    """내부 transcript를 provider 요청용 message item 목록으로 변환한다."""

    items: list[dict[str, Any]] = []
    for message in messages:
        items.extend(_message_to_responses_items(coerce_agent_message(message)))
    return items


def tools_to_responses_tools(tools: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """agent.loop의 function wrapper schema를 provider 요청 schema로 평탄화한다."""

    normalized: list[dict[str, Any]] = []
    for tool in tools or []:
        if not isinstance(tool, dict):
            continue
        if tool.get("type") == "function" and isinstance(tool.get("function"), dict):
            function = tool["function"]
            flat = {
                "type": "function",
                "name": function.get("name"),
                "description": function.get("description", ""),
                "parameters": function.get("parameters") or {},
            }
            if "strict" in function:
                flat["strict"] = function["strict"]
            normalized.append(flat)
        else:
            normalized.append(dict(tool))
    return normalized


def build_agent_model_response(
    *,
    provider_name: str,
    requested_model: str,
    response_json: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> AgentModelResponse:
    """provider 원본 응답에서 agent.loop가 필요한 텍스트, tool call, 사용량 정보를 추출한다."""

    output_text = extract_responses_output_text(response_json)
    response_contract = parse_assistant_response_contract(output_text)
    tool_calls = extract_responses_tool_calls(response_json)
    reasoning = extract_responses_reasoning(response_json)
    model = str(response_json.get("model") or requested_model)
    finish_reason = _resolve_finish_reason(response_json, tool_calls)
    usage = response_json.get("usage") if isinstance(response_json.get("usage"), dict) else {}
    message = AgentMessage(
        role="assistant",
        content=response_contract.get("raw_text") or output_text,
        tool_calls=tool_calls,
        metadata={
            "response_id": response_json.get("id"),
            "model": model,
            "status": response_json.get("status"),
            "raw_metadata": response_json.get("metadata") if isinstance(response_json.get("metadata"), dict) else {},
            "response_contract": response_contract.get("contract") or {},
        },
    )
    return AgentModelResponse(
        provider_name=provider_name,
        model=model,
        message=message,
        output_text=output_text,
        tool_calls=tool_calls,
        finish_reason=finish_reason,
        reasoning=reasoning,
        usage=usage,
        raw_response=response_json,
        progress_update=response_contract.get("progressUpdate"),
        work_disposition=response_contract.get("workDisposition"),
        visible_text=response_contract.get("text"),
        metadata={
            "response_id": response_json.get("id"),
            "model": model,
            "status": response_json.get("status"),
            "raw_metadata": response_json.get("metadata") if isinstance(response_json.get("metadata"), dict) else {},
            "response_contract": response_contract.get("contract") or {},
            **(metadata or {}),
        },
    )


def parse_assistant_response_contract(output_text: str) -> dict[str, Any]:
    """assistant text envelope를 provider 공통 실행 metadata로 정규화한다."""

    raw_text = str(output_text or "")
    parsed = _parse_json_object_from_text(raw_text)
    if not isinstance(parsed, dict):
        return {"text": raw_text, "raw_text": raw_text, "contract": {}}

    contract_keys = {"text", "answer", "progressUpdate", "workDisposition"}
    if not any(key in parsed for key in contract_keys):
        return {"text": raw_text, "raw_text": raw_text, "contract": {}}

    visible_text = parsed.get("text")
    if not isinstance(visible_text, str):
        visible_text = parsed.get("answer") if isinstance(parsed.get("answer"), str) else raw_text
    progress_update = parsed.get("progressUpdate") if isinstance(parsed.get("progressUpdate"), dict) else None
    work_disposition = parsed.get("workDisposition") if isinstance(parsed.get("workDisposition"), dict) else None
    return {
        "text": str(visible_text or "").strip(),
        "raw_text": raw_text,
        "progressUpdate": progress_update,
        "workDisposition": work_disposition,
        "contract": {
            "progressUpdate": progress_update,
            "workDisposition": work_disposition,
        },
    }


def extract_responses_output_text(response_json: dict[str, Any]) -> str:
    """provider 응답의 여러 content 위치에서 assistant 텍스트만 모은다."""

    direct = response_json.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct

    collected: list[str] = []
    for item in response_json.get("output", []):
        if not isinstance(item, dict):
            continue
        if item.get("type") == "message" or item.get("role") == "assistant":
            collected.extend(_extract_content_texts(item.get("content")))
    return "\n".join(text for text in collected if text)


def extract_responses_tool_calls(response_json: dict[str, Any]) -> list[AssistantToolCall]:
    """provider 응답에서 실행 가능한 native tool call만 추출한다."""

    tool_calls: list[AssistantToolCall] = []
    for item in response_json.get("output", []):
        if not isinstance(item, dict):
            continue
        if item.get("type") in {"function_call", "tool_call"}:
            tool_calls.append(coerce_assistant_tool_call(item))
            continue
        if item.get("type") == "message" or item.get("role") == "assistant":
            for tool_call in item.get("tool_calls") or []:
                tool_calls.append(coerce_assistant_tool_call(tool_call))
    return [tool_call for tool_call in tool_calls if tool_call.id and tool_call.name]


def extract_responses_reasoning(response_json: dict[str, Any]) -> Any:
    """reasoning 계열 원본 필드는 실행 로직에 쓰지 않고 관측용으로만 보존한다."""

    if "reasoning" in response_json:
        return response_json["reasoning"]
    if "reasoning_details" in response_json:
        return response_json["reasoning_details"]

    reasoning_items: list[dict[str, Any]] = []
    for item in response_json.get("output", []):
        if isinstance(item, dict) and item.get("type") == "reasoning":
            reasoning_items.append(item)
    return reasoning_items or None


def _message_to_responses_items(message: AgentMessage) -> list[dict[str, Any]]:
    """내부 메시지 하나를 provider request item 하나 이상으로 변환한다."""

    if message.role == "tool":
        return [
            {
                "type": "function_call_output",
                "call_id": message.tool_call_id,
                "output": _content_to_text(message.content),
            }
        ]

    items: list[dict[str, Any]] = []
    if message.content not in {None, ""} or not message.tool_calls:
        item: dict[str, Any] = {
            "role": message.role,
            "content": _message_content_to_responses_content(message),
        }
        if message.name:
            item["name"] = message.name
        items.append(item)
    items.extend(_tool_call_to_responses_item(tool_call) for tool_call in message.tool_calls)
    return items


def _message_content_to_responses_content(message: AgentMessage) -> str | list[dict[str, Any]]:
    content = message.content
    if isinstance(content, list):
        return content
    if content is None:
        return ""
    return str(content)


def _tool_call_to_responses_item(tool_call: AssistantToolCall) -> dict[str, Any]:
    return {
        "type": "function_call",
        "call_id": tool_call.id,
        "name": tool_call.name,
        "arguments": tool_call.arguments_json or json.dumps(tool_call.arguments, ensure_ascii=False),
    }


def _extract_content_texts(content: Any) -> list[str]:
    if isinstance(content, str):
        return [content]
    if not isinstance(content, list):
        return []

    texts: list[str] = []
    for part in content:
        if not isinstance(part, dict):
            continue
        text = part.get("text")
        if part.get("type") in {"output_text", "text"} and isinstance(text, str):
            texts.append(text)
    return texts


def _content_to_text(content: str | list[dict[str, Any]] | None) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = _extract_content_texts(content)
        if texts:
            return "\n".join(texts)
        return json.dumps(content, ensure_ascii=False)
    return ""


def _resolve_finish_reason(response_json: dict[str, Any], tool_calls: list[AssistantToolCall]) -> str | None:
    if tool_calls:
        return "tool_calls"
    for key in ("finish_reason", "stop_reason", "status"):
        value = response_json.get(key)
        if isinstance(value, str) and value:
            return value
    return "stop" if extract_responses_output_text(response_json).strip() else None


def _parse_json_object_from_text(text: str) -> dict[str, Any] | None:
    stripped = str(text or "").strip()
    if not stripped:
        return None
    candidates = [stripped]
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        candidates.insert(0, fenced.group(1).strip())
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None
