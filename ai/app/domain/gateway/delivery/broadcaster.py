from __future__ import annotations

from app.domain.gateway.delivery.envelope import build_websocket_event
from app.domain.gateway.routing.topic_router import TopicRouter


class EventBroadcaster:
    """Publish task events through gateway routing and transport adapters."""

    def __init__(self, manager, topic_router: TopicRouter | None = None) -> None:
        self.manager = manager
        self.topic_router = topic_router or TopicRouter()

    async def publish(self, event) -> None:
        topic = self.topic_router.topic_for_event(event)
        payload = build_websocket_event(event)
        await self.manager.broadcast(payload, topic)
