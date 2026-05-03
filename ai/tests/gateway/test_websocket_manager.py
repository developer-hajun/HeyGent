from __future__ import annotations

import asyncio

from app.domain.gateway.platforms.websocket import WebSocketManager


class FakeWebSocket:
    """테스트에서 Starlette WebSocket 대신 쓰는 최소 객체다."""

    def __init__(self, *, delay_seconds: float = 0.0, fail: bool = False) -> None:
        self.delay_seconds = delay_seconds
        self.fail = fail
        self.accepted = False
        self.sent: list[dict] = []
        self.concurrent_sends = 0
        self.max_concurrent_sends = 0

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, event: dict) -> None:
        self.concurrent_sends += 1
        self.max_concurrent_sends = max(self.max_concurrent_sends, self.concurrent_sends)
        try:
            if self.delay_seconds:
                await asyncio.sleep(self.delay_seconds)
            if self.fail:
                raise RuntimeError("send failed")
            self.sent.append(event)
        finally:
            self.concurrent_sends -= 1


async def test_connect_accepts_socket_and_broadcast_delivers_topic_event():
    manager = WebSocketManager()
    websocket = FakeWebSocket()
    event = {"type": "task.event", "data": {"taskRunId": "task_1"}}

    await manager.connect(websocket)
    manager.subscribe(websocket, "task:task_1")
    await manager.broadcast(event, "task:task_1")

    assert websocket.accepted is True
    assert websocket.sent == [event]


async def test_broadcast_uses_all_topic_subscription():
    manager = WebSocketManager()
    websocket = FakeWebSocket()
    event = {"type": "system.notice"}

    await manager.connect(websocket)
    manager.subscribe(websocket, manager.topic_router.all_topic())
    await manager.broadcast(event, "task:task_1")

    assert websocket.sent == [event]


async def test_broadcast_removes_socket_when_send_fails():
    manager = WebSocketManager()
    websocket = FakeWebSocket(fail=True)

    await manager.connect(websocket)
    manager.subscribe(websocket, "task:task_1")
    await manager.broadcast({"type": "task.event"}, "task:task_1")

    assert manager.directory.get("task:task_1") == set()


async def test_broadcast_does_not_wait_for_slow_socket_before_fast_socket():
    manager = WebSocketManager(send_timeout_seconds=0.01)
    slow_socket = FakeWebSocket(delay_seconds=0.1)
    fast_socket = FakeWebSocket()
    event = {"type": "task.event", "sequence": 1}

    await manager.connect(slow_socket)
    await manager.connect(fast_socket)
    manager.subscribe(slow_socket, "task:task_1")
    manager.subscribe(fast_socket, "task:task_1")

    await manager.broadcast(event, "task:task_1")

    assert fast_socket.sent == [event]
    assert manager.directory.get("task:task_1") == {fast_socket}


async def test_send_json_serializes_writes_for_same_socket():
    manager = WebSocketManager()
    websocket = FakeWebSocket(delay_seconds=0.01)

    await manager.connect(websocket)
    await asyncio.gather(
        manager.send_json(websocket, {"type": "first"}),
        manager.send_json(websocket, {"type": "second"}),
    )

    assert len(websocket.sent) == 2
    assert websocket.max_concurrent_sends == 1
