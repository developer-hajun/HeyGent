"""진행 상황 emit 관련 컴포넌트.

ToolCallingLoop의 진행 상황 emit 관련 메서드들을 위임받는 thin adapter다.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.domain.orchestration.agent.tool_calling_loop import ToolCallingLoop


class ProgressEmitter:
    """진행 상황 emit 관련 컴포넌트."""

    def __init__(self, loop: "ToolCallingLoop") -> None:
        self._loop = loop

    async def emit_tool_progress(self, **kwargs: Any) -> None:
        await self._loop._emit_tool_progress(**kwargs)

    async def emit_model_call_progress(self, **kwargs: Any) -> None:
        await self._loop._emit_model_call_progress(**kwargs)

    async def emit_model_progress_update(self, **kwargs: Any) -> None:
        await self._loop._emit_model_progress_update(**kwargs)
