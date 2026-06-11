"""세션 목록 조회 핸들러.

CommandRouter의 세션 목록 관련 메서드들을 위임받는 thin adapter다.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.api.ws.commands import CommandRouter


class SessionListHandler:
    """세션 목록 조회 핸들러."""

    def __init__(self, router: "CommandRouter") -> None:
        self._router = router

    async def session_list(self, payload: dict[str, Any], context: Any) -> tuple[str, dict[str, Any]]:
        return await self._router._session_list(payload, context)

    async def session_messages_list(self, payload: dict[str, Any], context: Any) -> tuple[str, dict[str, Any]]:
        return await self._router._session_messages_list(payload, context)
