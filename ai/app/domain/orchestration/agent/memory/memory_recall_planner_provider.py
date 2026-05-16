from __future__ import annotations

import json
from typing import Any

from app.api.memory_context import MemoryRecallPlan
from app.domain.orchestration.agent.memory.provider_retry import respond_provider_with_retry
from app.domain.providers.model.base import AgentMessage
from app.domain.providers.registry import ProviderRegistry


class ProviderMemoryRecallPlannerClient:
    """기존 Model Provider를 사용해 memory recall planning JSON을 받아온다."""

    def __init__(self, *, provider_registry: ProviderRegistry, model: str | None = None) -> None:
        self._provider_registry = provider_registry
        self._model = model

    async def plan_memory_recall_json(
        self,
        *,
        system_prompt: str,
        query: str,
        workspace_key: str | None,
        rule_plan: MemoryRecallPlan,
    ) -> dict[str, Any]:
        provider = self._provider_registry.preferred_model_provider()
        _ensure_live_provider(provider)
        model = self._model or str(getattr(getattr(provider, "settings", None), "openai_response_model", "") or "gpt-5.4")
        payload = {
            "query": query,
            "workspaceKey": workspace_key,
            "rulePlanHint": {
                "shouldRecall": rule_plan.should_recall,
                "reason": rule_plan.reason,
                "filters": rule_plan.filters(),
            },
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
        raise ValueError("memory recall planner response must be a JSON object")
    return parsed


def _ensure_live_provider(provider) -> None:
    health = provider.health()
    if not bool(getattr(health, "connected", False)):
        raise RuntimeError("memory provider requires a connected model provider")
