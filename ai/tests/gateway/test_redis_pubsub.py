from __future__ import annotations

from app.contracts.event.task_events import TaskEventEnvelope
from app.domain.gateway.delivery.broadcaster import EventBroadcaster
from app.domain.gateway.delivery.redis_pubsub import RedisFanoutPublisher, RedisFanoutSubscriber


class FakeRedisPubSubClient:
    def __init__(self) -> None:
        self.published: list[tuple[str, str]] = []

    def publish(self, channel: str, message: str) -> int:
        self.published.append((channel, message))
        return 1


class FakePubSub:
    def __init__(self, messages: list[dict]) -> None:
        self.messages = list(messages)
        self.subscribed: list[str] = []
        self.closed = False

    def psubscribe(self, pattern: str) -> None:
        self.subscribed.append(pattern)

    def get_message(self, *, ignore_subscribe_messages: bool = True, timeout: float = 1.0):
        if self.messages:
            return self.messages.pop(0)
        return None

    def close(self) -> None:
        self.closed = True


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
    assert '"publisherId":"' in message


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


async def test_redis_fanout_subscriber_ignores_current_process_echo():
    manager = FakeWebSocketManager()
    subscriber = RedisFanoutSubscriber(manager, ignored_publisher_id="publisher_self")
    message = (
        '{"publisherId":"publisher_self","topic":"task:task_pubsub","payload":{"type":"task.event",'
        '"data":{"event_id":"event_pubsub","event_type":"task.updated",'
        '"task_run_id":"task_pubsub","producer":"test","occurred_at":"2026-04-29T00:00:00+00:00"}}}'
    )

    await subscriber.handle_message(message)

    assert manager.broadcasts == []


async def test_event_broadcaster_uses_local_broadcast_before_redis_fanout():
    redis = FakeRedisPubSubClient()
    manager = FakeWebSocketManager()
    publisher = RedisFanoutPublisher(redis)
    broadcaster = EventBroadcaster(manager, fanout_publisher=publisher)
    event = TaskEventEnvelope(
        event_id="event_broadcast",
        event_type="task.updated",
        task_run_id="task_broadcast",
        producer="test",
        occurred_at="2026-04-29T00:00:00+00:00",
    )

    await broadcaster.publish(event)

    assert len(redis.published) == 1
    assert manager.broadcasts[0][1] == "task:task_broadcast"
    assert manager.broadcasts[0][0]["type"] == "task.event"


async def test_redis_fanout_subscriber_loop_reads_pubsub_messages_until_stopped():
    manager = FakeWebSocketManager()
    subscriber = RedisFanoutSubscriber(manager)
    pubsub = FakePubSub(
        [
            {
                "type": "message",
                "data": (
                    '{"topic":"task:task_loop","payload":{"type":"task.event",'
                    '"data":{"event_id":"event_loop","event_type":"task.updated",'
                    '"task_run_id":"task_loop","producer":"test","occurred_at":"2026-04-29T00:00:00+00:00"}}}'
                ),
            }
        ]
    )

    await subscriber.run_once(pubsub)

    assert pubsub.subscribed == ["heygent:ai:ws:topic:*"]
    assert manager.broadcasts[0][1] == "task:task_loop"
