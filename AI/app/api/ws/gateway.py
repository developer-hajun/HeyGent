from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws")
async def websocket_gateway(websocket: WebSocket) -> None:
    manager = websocket.app.state.ws_manager
    await manager.connect(websocket)
    try:
        while True:
            message = await websocket.receive_json()
            action = message.get("action")
            if action == "subscribe" and message.get("task_run_id"):
                manager.subscribe(websocket, message["task_run_id"])
                await websocket.send_json({"type": "subscribed", "task_run_id": message["task_run_id"]})
            elif action == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
