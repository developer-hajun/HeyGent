from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.ws.subscriptions import handle_subscription

router = APIRouter()


@router.websocket("/ws")
async def websocket_gateway(websocket: WebSocket) -> None:
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
