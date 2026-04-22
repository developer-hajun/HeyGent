from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.ws.subscriptions import handle_subscription

router = APIRouter()


async def _handle_gateway_socket(websocket: WebSocket) -> None:
    manager = websocket.app.state.ws_manager
    session_registry = websocket.app.state.session_registry
    session_id = websocket.query_params.get("session_id", "anonymous")
    await manager.connect(websocket)
    try:
        while True:
            message = await websocket.receive_json()
            action = message.get("action")
            if action == "subscribe" and message.get("task_run_id"):
                await handle_subscription(
                    websocket,
                    manager=manager,
                    session_registry=session_registry,
                    session_id=session_id,
                    task_run_id=message["task_run_id"],
                )
            elif action == "subscribe_all":
                manager.subscribe(websocket, "all")
                await websocket.send_json({"type": "subscribed", "task_run_id": "all"})
            elif action == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        session_registry.unsubscribe_all(session_id)
        manager.disconnect(websocket)


@router.websocket("/gateway/ws")
async def websocket_gateway(websocket: WebSocket) -> None:
    """권장 WebSocket 경로다.

    HTTP 표면이 `/api/v1/...` 로 정리된 뒤에는,
    WebSocket 도 단순 `/ws` 보다 `/gateway/ws` 가 역할을 더 명확히 보여 준다.
    """

    await _handle_gateway_socket(websocket)


@router.websocket("/ws")
async def websocket_gateway_legacy(websocket: WebSocket) -> None:
    """이전 테스트나 임시 클라이언트를 위한 호환 경로다."""

    await _handle_gateway_socket(websocket)
