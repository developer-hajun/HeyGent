from __future__ import annotations

import asyncio
import json
from typing import Any

from app.domain.providers.model.base import AgentMessage
from app.domain.providers.registry import ProviderRegistry


class ProviderMemoryUsageAttributionClient:
    """기존 Model Provider로 recalled memory 사용 여부 판단 JSON을 받아온다."""

    def __init__(self, *, provider_registry: ProviderRegistry, model: str | None = None) -> None:
        self._provider_registry = provider_registry
        self._model = model

    async def verify_memory_usage_json(
        self,
        *,
        system_prompt: str,
        user_query: str,
        assistant_message: str,
        recalled_memories: list[dict[str, Any]],
    ) -> dict[str, Any]:
        provider = self._provider_registry.preferred_model_provider()
        _ensure_live_provider(provider)
        provider_settings = getattr(provider, "settings", None)
        model = self._model or str(getattr(provider_settings, "openai_response_model", "") or "gpt-5.4")
        payload = {
            "userQuery": user_query,
            "assistantMessage": assistant_message,
            "recalledMemories": recalled_memories,
        }
        response = await _respond_provider_async(
            provider,
            messages=[
                AgentMessage(role="system", content=system_prompt),
                AgentMessage(role="user", content=json.dumps(payload, ensure_ascii=False)),
            ],
            tools=None,
            model=model,
            tool_choice=None,
        )
        return _parse_json_object(response.output_text)


def _parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    parsed = json.loads(stripped)
    if not isinstance(parsed, dict):
        raise ValueError("memory usage attribution response must be a JSON object")
    return parsed


async def _respond_provider_async(provider, **kwargs):
    respond_async = getattr(provider, "respond_async", None)
    if callable(respond_async):
        return await respond_async(**kwargs)
    return await asyncio.to_thread(provider.respond, **kwargs)


def _ensure_live_provider(provider) -> None:
    health = provider.health()
    if not bool(getattr(health, "connected", False)):
        raise RuntimeError("memory provider requires a connected model provider")
