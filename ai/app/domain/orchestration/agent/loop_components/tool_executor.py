"""툴 실행 관련 컴포넌트.

ToolCallingLoop의 툴 실행 관련 메서드들을 위임받는 thin adapter다.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.domain.orchestration.agent.tool_calling_loop import ToolCallingLoop


class ToolExecutor:
    """툴 실행 관련 컴포넌트."""

    def __init__(self, loop: "ToolCallingLoop") -> None:
        self._loop = loop

    def run_native_tool_call(self, *, tool_name: str, args: dict[str, Any], tool_call_id: str, runtime) -> dict[str, Any]:
        return self._loop._run_native_tool_call(tool_name=tool_name, args=args, tool_call_id=tool_call_id, runtime=runtime)

    async def execute_delegate_tool_result(self, **kwargs: Any) -> dict[str, Any]:
        return await self._loop._execute_delegate_tool_result(**kwargs)

    async def execute_session_agent_tool_result(self, **kwargs: Any) -> dict[str, Any]:
        return await self._loop._execute_session_agent_tool_result(**kwargs)
