from __future__ import annotations

from app.domain.gateway.delivery.envelope import build_websocket_event
from app.domain.gateway.routing.topic_router import TopicRouter


class EventBroadcaster:
    """Task event를 local WebSocket 또는 Redis fan-out 경로로 발행한다."""

    def __init__(self, manager, topic_router: TopicRouter | None = None, fanout_publisher=None) -> None:
        self.manager = manager
        self.topic_router = topic_router or TopicRouter()
        self.fanout_publisher = fanout_publisher

    async def publish(self, event) -> None:
        if self.fanout_publisher is not None:
            # Redis Pub/Sub subscriber가 local socket 전송을 담당하므로 같은 인스턴스 중복 전송을 피한다.
            await self.fanout_publisher.publish(event)
            return
        topic = self.topic_router.topic_for_event(event)
        payload = build_websocket_event(event)
        await self.manager.broadcast(payload, topic)
