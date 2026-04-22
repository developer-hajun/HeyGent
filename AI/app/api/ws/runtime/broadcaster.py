from __future__ import annotations

from app.contracts.event.ws_events import WebSocketEvent
from app.api.ws.runtime.ws_manager import WebSocketManager


class EventBroadcaster:
    """저장된 이벤트를 WS 표면으로 다시 감싼다."""

    def __init__(self, manager: WebSocketManager) -> None:
        self.manager = manager

    async def publish(self, event) -> None:
        ws_event = WebSocketEvent(data=event)
        await self.manager.broadcast(ws_event.model_dump(mode="json"), event.task_run_id)
