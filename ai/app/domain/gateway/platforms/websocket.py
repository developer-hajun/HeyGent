from __future__ import annotations

from fastapi import WebSocket

from app.domain.gateway.routing.channel_directory import ChannelDirectory
from app.domain.gateway.routing.topic_router import TopicRouter


class WebSocketManager:
    """Websocket transport adapter for gateway delivery."""

    def __init__(self, directory: ChannelDirectory | None = None, topic_router: TopicRouter | None = None) -> None:
        self.directory = directory or ChannelDirectory()
        self.topic_router = topic_router or TopicRouter()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()

    def disconnect(self, websocket: WebSocket) -> None:
        self.directory.discard(websocket)

    def subscribe(self, websocket: WebSocket, topic: str) -> None:
        self.directory.add(topic, websocket)

    async def broadcast(self, event: dict, topic: str) -> None:
        targets = self.directory.get(topic)
        targets.update(self.directory.get(self.topic_router.all_topic()))
        stale: list[WebSocket] = []
        for websocket in targets:
            try:
                await websocket.send_json(event)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(websocket)
