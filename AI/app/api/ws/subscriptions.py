from __future__ import annotations

from fastapi import WebSocket

from app.domain.gateway.session_registry import SessionRegistry
from app.domain.gateway.ws_manager import WebSocketManager


async def handle_subscription(
    websocket: WebSocket,
    *,
    manager: WebSocketManager,
    session_registry: SessionRegistry,
    session_id: str,
    task_run_id: str,
) -> None:
    """웹소켓 구독 처리와 세션 기록을 분리한다."""

    manager.subscribe(websocket, task_run_id)
    session_registry.subscribe(session_id, task_run_id)
    await websocket.send_json({"type": "subscribed", "task_run_id": task_run_id})
