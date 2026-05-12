"""웹 페이지 요약과 브라우저 화면 해석에 쓰는 보조 LLM 호출 모듈.

검색/브라우저 도구가 긴 HTML, 문서 본문, 스크린샷을 그대로 반환하면
대화 맥락이 급격히 커진다. 이 모듈은 OpenAI API 형식의 호출로 내용을
짧게 요약하거나 화면 설명을 생성해 도구 결과를 다루기 쉽게 만든다.
"""

from __future__ import annotations

import os
from typing import Any

from openai import AsyncOpenAI, OpenAI


DEFAULT_TEXT_MODEL = os.getenv("AUXILIARY_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
DEFAULT_VISION_MODEL = os.getenv("AUXILIARY_VISION_MODEL", DEFAULT_TEXT_MODEL)


def _api_key() -> str | None:
    value = os.getenv("OPENAI_API_KEY") or os.getenv("HEYGENT_OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    return value.strip() if isinstance(value, str) and value.strip() else None


def _base_url() -> str | None:
    value = (
        os.getenv("OPENAI_BASE_URL")
        or os.getenv("HEYGENT_OPENAI_REST_API_BASE_URL")
        or os.getenv("OPENROUTER_BASE_URL")
    )
    return value.strip() if isinstance(value, str) and value.strip() else None


def get_async_text_auxiliary_client(task: str | None = None) -> tuple[Any | None, str | None]:
    api_key = _api_key()
    if not api_key:
        return None, None
    kwargs: dict[str, str] = {"api_key": api_key}
    base_url = _base_url()
    if base_url:
        kwargs["base_url"] = base_url
    model = os.getenv(f"AUXILIARY_{str(task or '').upper()}_MODEL", "").strip() or DEFAULT_TEXT_MODEL
    return AsyncOpenAI(**kwargs), model


def get_auxiliary_extra_body() -> dict[str, Any]:
    return {}


async def async_call_llm(**kwargs: Any) -> Any:
    task = str(kwargs.pop("task", "") or "")
    client, default_model = get_async_text_auxiliary_client(task)
    if client is None:
        raise RuntimeError("No auxiliary OpenAI-compatible API key configured")
    model = str(kwargs.pop("model", None) or default_model or DEFAULT_TEXT_MODEL)
    messages = kwargs.pop("messages")
    return await client.chat.completions.create(model=model, messages=messages, **kwargs)


def call_llm(**kwargs: Any) -> Any:
    api_key = _api_key()
    if not api_key:
        raise RuntimeError("No auxiliary OpenAI-compatible API key configured")
    client_kwargs: dict[str, str] = {"api_key": api_key}
    base_url = _base_url()
    if base_url:
        client_kwargs["base_url"] = base_url
    client = OpenAI(**client_kwargs)
    model = str(kwargs.pop("model", None) or DEFAULT_VISION_MODEL)
    messages = kwargs.pop("messages")
    kwargs.pop("task", None)
    return client.chat.completions.create(model=model, messages=messages, **kwargs)


def extract_content_or_reasoning(response: Any) -> str:
    choices = getattr(response, "choices", None)
    if choices:
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text") or item.get("content")
                    if isinstance(text, str):
                        parts.append(text)
                elif isinstance(item, str):
                    parts.append(item)
            return "\n".join(parts)
    output_text = getattr(response, "output_text", None)
    return output_text if isinstance(output_text, str) else ""
