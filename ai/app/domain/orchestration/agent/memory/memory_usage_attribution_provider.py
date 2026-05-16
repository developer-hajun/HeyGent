from __future__ import annotations

import json
from typing import Any

from app.domain.orchestration.agent.memory.provider_retry import respond_provider_with_retry
from app.domain.providers.model.base import AgentMessage
from app.domain.providers.registry import ProviderRegistry


class ProviderMemoryUsageAttributionClient:
    """기존 Model Provider로 recalled memory 사용 여부 판단 JSON을 받아온다."""

    def __init__(self, *, provider_registry: ProviderRegistry, model: str | None = None) -> None:
        self._provider_registry = provider_registry
        self._model = model
        self.last_memory_provider_meta: dict[str, Any] = {}

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
        self.last_memory_provider_meta = {
            "provider_name": str(getattr(provider, "name", None) or provider.__class__.__name__),
            "selected_model": model,
        }
        payload = {
            "userQuery": user_query,
            "assistantMessage": assistant_message,
            "recalledMemories": recalled_memories,
        }
        response = await respond_provider_with_retry(
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


def _ensure_live_provider(provider) -> None:
    health = provider.health()
    if not bool(getattr(health, "connected", False)):
        raise RuntimeError("memory provider requires a connected model provider")
