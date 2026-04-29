from __future__ import annotations

import json
from typing import Any

from app.domain.gateway.delivery.envelope import build_websocket_event
from app.domain.gateway.routing.topic_router import TopicRouter


class RedisFanoutPublisher:
    """다중 AI 서버 인스턴스에 WebSocket event를 전달하기 위한 Redis Pub/Sub publisher다."""

    def __init__(self, redis_client: Any, topic_router: TopicRouter | None = None) -> None:
        self.redis = redis_client
        self.topic_router = topic_router or TopicRouter()

    async def publish(self, event) -> None:
        topic = self.topic_router.topic_for_event(event)
        message = {
            "topic": topic,
            "payload": build_websocket_event(event),
        }
        self.redis.publish(self._channel_for_topic(topic), json.dumps(message, ensure_ascii=False, separators=(",", ":")))

    @staticmethod
    def _channel_for_topic(topic: str) -> str:
        return f"heygent:ai:ws:topic:{topic}"


class RedisFanoutSubscriber:
    """Redis Pub/Sub message를 현재 프로세스의 WebSocketManager로 fan-out한다."""

    def __init__(self, manager) -> None:
        self.manager = manager

    async def handle_message(self, message: str | bytes | dict) -> None:
        decoded = self._decode_message(message)
        topic = str(decoded["topic"])
        payload = decoded["payload"]
        # Pub/Sub은 replay 저장소가 아니므로, 수신한 payload는 현재 살아 있는 local socket에만 전달한다.
        await self.manager.broadcast(payload, topic)

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
