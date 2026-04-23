from __future__ import annotations

from fastapi import WebSocket

from app.domain.gateway.sessions.session_service import SessionService


async def handle_subscription(
    websocket: WebSocket,
    *,
    session_service: SessionService,
    session_id: str,
    task_run_id: str,
) -> None:
    """웹소켓 구독 처리와 세션 기록을 분리한다."""

    session_service.subscribe_task(session_id=session_id, websocket=websocket, task_run_id=task_run_id)
    await websocket.send_json({"type": "subscribed", "task_run_id": task_run_id})
