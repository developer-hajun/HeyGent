from __future__ import annotations

from app.contracts.event.ws_events import WebSocketEvent


def build_websocket_event(event) -> dict:
    return WebSocketEvent(data=event).model_dump(mode="json", by_alias=True)
