"""Work 보드 관련 핸들러.

CommandRouter의 work 관련 메서드들을 위임받는 thin adapter다.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.api.ws.commands import CommandRouter


class WorkHandler:
    """Work 보드 관련 핸들러."""

    def __init__(self, router: "CommandRouter") -> None:
        self._router = router

    async def task_runs_active_list(self, payload: dict[str, Any], context: Any) -> tuple[str, dict[str, Any]]:
        return await self._router._task_runs_active_list(payload, context)

    async def task_run_snapshot_get(self, payload: dict[str, Any], context: Any) -> tuple[str, dict[str, Any]]:
        return await self._router._task_run_snapshot_get(payload, context)

    async def task_run_events_replay(self, payload: dict[str, Any], context: Any) -> tuple[str, dict[str, Any]]:
        return await self._router._task_run_events_replay(payload, context)

    async def task_run_resume(self, payload: dict[str, Any], context: Any) -> tuple[str, dict[str, Any]]:
        return await self._router._task_run_resume(payload, context)

    async def task_run_cancel(self, payload: dict[str, Any], context: Any) -> tuple[str, dict[str, Any]]:
        return await self._router._task_run_cancel(payload, context)
