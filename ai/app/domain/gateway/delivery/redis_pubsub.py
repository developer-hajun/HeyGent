from __future__ import annotations

import json
import asyncio
from uuid import uuid4
from typing import Any

from app.domain.gateway.delivery.envelope import build_websocket_event
from app.domain.gateway.routing.topic_router import TopicRouter


class RedisFanoutPublisher:
    """다중 AI 서버 인스턴스에 WebSocket event를 전달하기 위한 Redis Pub/Sub publisher다.

    redis.asyncio 클라이언트를 사용해 await redis.publish()로 이벤트 루프를 블로킹하지 않는다.
    """

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
        serialized = json.dumps(message, ensure_ascii=False, separators=(",", ":"))
        channel = self._channel_for_topic(topic)
        try:
            await self.redis.publish(channel, serialized)
        except Exception:
            # publish 실패가 응답 생성을 막지 않도록 best-effort로 처리한다.
            pass

    @staticmethod
    def _channel_for_topic(topic: str) -> str:
        return f"heygent:ai:ws:topic:{topic}"


class RedisFanoutSubscriber:
    """Redis Pub/Sub message를 현재 프로세스의 WebSocketManager로 fan-out한다.

    redis.asyncio의 async pubsub을 사용해 폴링 sleep 없이 메시지 도착 즉시 처리한다.
    """

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
        await self.manager.broadcast(payload, topic)

    async def run_forever(self, async_redis_client: Any, *, pattern: str = "heygent:ai:ws:topic:*") -> None:
        """앱 lifespan에서 실행할 비동기 Pub/Sub subscriber loop다.

        redis.asyncio pubsub의 listen()을 사용해 메시지 도착을 즉시 처리한다.
        기존 방식의 asyncio.to_thread + sleep(0.1) 패턴 대비 최대 100ms 지연이 제거된다.
        """
        pubsub = async_redis_client.pubsub()
        try:
            await pubsub.psubscribe(pattern)
            async for message in pubsub.listen():
                if message is None:
                    continue
                msg_type = message.get("type") if isinstance(message, dict) else None
                if msg_type not in ("message", "pmessage"):
                    continue
                try:
                    await self.handle_message(message)
                except Exception:
                    pass
        finally:
            try:
                await pubsub.punsubscribe(pattern)
                await pubsub.aclose()
            except Exception:
                pass

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
