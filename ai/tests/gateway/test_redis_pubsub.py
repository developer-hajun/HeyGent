from __future__ import annotations

from app.contracts.event.task_events import TaskEventEnvelope
from app.domain.gateway.delivery.redis_pubsub import RedisFanoutPublisher, RedisFanoutSubscriber


class FakeRedisPubSubClient:
    def __init__(self) -> None:
        self.published: list[tuple[str, str]] = []

    def publish(self, channel: str, message: str) -> int:
        self.published.append((channel, message))
        return 1


class FakeWebSocketManager:
    def __init__(self) -> None:
        self.broadcasts: list[tuple[dict, str]] = []

    async def broadcast(self, event: dict, topic: str) -> None:
        self.broadcasts.append((event, topic))


async def test_redis_fanout_publisher_serializes_task_event_to_channel():
    redis = FakeRedisPubSubClient()
    publisher = RedisFanoutPublisher(redis)
    event = TaskEventEnvelope(
        event_id="event_pubsub",
        event_type="task.updated",
        task_run_id="task_pubsub",
        producer="test",
        occurred_at="2026-04-29T00:00:00+00:00",
        sequence=7,
    )

    await publisher.publish(event)

    channel, message = redis.published[0]
    assert channel == "heygent:ai:ws:topic:task:task_pubsub"
    assert '"sequence":7' in message
    assert '"eventId":"event_pubsub"' in message


async def test_redis_fanout_subscriber_delivers_message_to_local_websocket_manager():
    manager = FakeWebSocketManager()
    subscriber = RedisFanoutSubscriber(manager)
    message = (
        '{"topic":"task:task_pubsub","payload":{"type":"task.event",'
        '"data":{"event_id":"event_pubsub","event_type":"task.updated",'
        '"task_run_id":"task_pubsub","producer":"test","occurred_at":"2026-04-29T00:00:00+00:00"}}}'
    )

    await subscriber.handle_message(message)

    assert manager.broadcasts[0][1] == "task:task_pubsub"
    assert manager.broadcasts[0][0]["type"] == "task.event"
