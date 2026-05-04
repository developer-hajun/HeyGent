from __future__ import annotations

import json
import asyncio
from uuid import uuid4
from typing import Any

from app.domain.gateway.delivery.envelope import build_websocket_event
from app.domain.gateway.routing.topic_router import TopicRouter


class RedisFanoutPublisher:
    """다중 AI 서버 인스턴스에 WebSocket event를 전달하기 위한 Redis Pub/Sub publisher다."""

    def __init__(
        self,
        redis_client: Any,
        topic_router: TopicRouter | None = None,
        *,
        publisher_id: str | None = None,
    ) -> None:
        self.redis = redis_client
        self.topic_router = topic_router or TopicRouter()
        self.publisher_id = publisher_id or f"publisher_{uuid4().hex}"

    async def publish(self, event) -> None:
        topic = self.topic_router.topic_for_event(event)
        message = {
            "topic": topic,
            "payload": build_websocket_event(event),
            "publisherId": self.publisher_id,
        }
        self.redis.publish(self._channel_for_topic(topic), json.dumps(message, ensure_ascii=False, separators=(",", ":")))

    @staticmethod
    def _channel_for_topic(topic: str) -> str:
        return f"heygent:ai:ws:topic:{topic}"


class RedisFanoutSubscriber:
    """Redis Pub/Sub message를 현재 프로세스의 WebSocketManager로 fan-out한다."""

    def __init__(self, manager, *, ignored_publisher_id: str | None = None) -> None:
        self.manager = manager
        self.ignored_publisher_id = ignored_publisher_id

    async def handle_message(self, message: str | bytes | dict) -> None:
        decoded = self._decode_message(message)
        if (
            self.ignored_publisher_id is not None
            and decoded.get("publisherId") == self.ignored_publisher_id
        ):
            # 같은 프로세스는 이미 local broadcast를 했으므로 Redis echo를 다시 보내지 않는다.
            return
        topic = str(decoded["topic"])
        payload = decoded["payload"]
        # Pub/Sub은 replay 저장소가 아니므로, 수신한 payload는 현재 살아 있는 local socket에만 전달한다.
        await self.manager.broadcast(payload, topic)

    async def run_once(self, pubsub) -> bool:
        """테스트와 lifecycle loop가 공유하는 단일 Pub/Sub poll 단위다."""

        if not getattr(pubsub, "_heygent_psubscribed", False):
            pubsub.psubscribe("heygent:ai:ws:topic:*")
            pubsub._heygent_psubscribed = True
        message = await asyncio.to_thread(
            pubsub.get_message,
            ignore_subscribe_messages=True,
            timeout=1.0,
        )
        if not message:
            return False
        if isinstance(message, dict) and message.get("type") not in {None, "message", "pmessage"}:
            return False
        await self.handle_message(message)
        return True

    async def run_forever(self, pubsub, *, poll_interval_seconds: float = 0.1) -> None:
        """앱 lifespan에서 실행할 Pub/Sub subscriber loop다."""

        try:
            while True:
                delivered = await self.run_once(pubsub)
                if not delivered:
                    await asyncio.sleep(poll_interval_seconds)
        finally:
            close = getattr(pubsub, "close", None)
            if callable(close):
                close()

    @staticmethod
    def _decode_message(message: str | bytes | dict) -> dict:
        if isinstance(message, dict):
            raw_data = message.get("data", message)
            if isinstance(raw_data, dict):
                return raw_data
            message = raw_data
        if isinstance(message, bytes):
            message = message.decode("utf-8")
        return json.loads(str(message))
