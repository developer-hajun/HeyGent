from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class WebSocketManager:
    """TaskRun 구독 단위로 연결을 관리한다."""

    def __init__(self) -> None:
        self._task_connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()

    def disconnect(self, websocket: WebSocket) -> None:
        for sockets in self._task_connections.values():
            sockets.discard(websocket)

    def subscribe(self, websocket: WebSocket, task_run_id: str) -> None:
        self._task_connections[task_run_id].add(websocket)

    async def broadcast(self, event: dict[str, Any], task_run_id: str) -> None:
        targets = set(self._task_connections[task_run_id])
        targets.update(self._task_connections["all"])
        stale: list[WebSocket] = []
        for websocket in targets:
            try:
                await websocket.send_json(event)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(websocket)
