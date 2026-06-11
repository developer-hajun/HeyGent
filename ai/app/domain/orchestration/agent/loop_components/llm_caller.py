"""LLM 호출 관련 컴포넌트.

ToolCallingLoop의 LLM 호출 관련 메서드들을 위임받는 thin adapter다.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.domain.orchestration.agent.tool_calling_loop import ToolCallingLoop


class LlmCaller:
    """LLM 호출 관련 컴포넌트."""

    def __init__(self, loop: "ToolCallingLoop") -> None:
        self._loop = loop

    def respond_with_runtime_context(self, messages: Any, tools: Any, model: str, tool_choice: Any, runtime_context: Any) -> Any:
        return self._loop._respond_with_runtime_context(messages, tools, model, tool_choice, runtime_context)

    async def respond_with_runtime_context_async(self, messages: Any, tools: Any, model: str, tool_choice: Any, runtime_context: Any, **kwargs: Any) -> Any:
        return await self._loop._respond_with_runtime_context_async(messages, tools, model, tool_choice, runtime_context, **kwargs)
