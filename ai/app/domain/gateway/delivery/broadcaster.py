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
        topic = self.topic_router.topic_for_event(event)
        payload = build_websocket_event(event)
        if self.fanout_publisher is not None:
            # 같은 프로세스의 WebSocket에는 즉시 보낸다. Redis Pub/Sub subscriber는 agent loop가
            # 긴 provider/tool 호출 중일 때 같은 event loop에서 늦게 돌 수 있어서, Pub/Sub만 의존하면
            # step.created/step.started가 최종 답변 뒤에 한꺼번에 보인다.
            await self.manager.broadcast(payload, topic)
            await self.fanout_publisher.publish(event)
            return
        await self.manager.broadcast(payload, topic)
