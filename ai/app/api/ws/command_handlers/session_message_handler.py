"""세션 메시지 create/retry/undo 핸들러.

CommandRouter의 메시지 관련 메서드들을 위임받는 thin adapter다.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.api.ws.commands import CommandRouter


class SessionMessageHandler:
    """세션 메시지 create/retry/undo 핸들러."""

    def __init__(self, router: "CommandRouter") -> None:
        self._router = router

    async def session_message_create(self, payload: dict[str, Any], context: Any) -> tuple[str, dict[str, Any]]:
        return await self._router._session_message_create(payload, context)

    async def session_message_retry(self, payload: dict[str, Any], context: Any) -> tuple[str, dict[str, Any]]:
        return await self._router._session_message_retry(payload, context)

    async def session_message_undo(self, payload: dict[str, Any], context: Any) -> tuple[str, dict[str, Any]]:
        return await self._router._session_message_undo(payload, context)
