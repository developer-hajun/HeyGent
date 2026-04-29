from __future__ import annotations

from app.contracts.event.ws_events import WebSocketEvent


def build_websocket_event(event) -> dict:
    payload = WebSocketEvent(data=event).model_dump(mode="json", by_alias=True)
    data = payload.get("data")
    if isinstance(data, dict) and not data.get("eventId"):
        # client dedupe 편의를 위해 snake_case 원본과 camelCase alias를 항상 같이 보낸다.
        data["eventId"] = data.get("event_id")
    return payload
