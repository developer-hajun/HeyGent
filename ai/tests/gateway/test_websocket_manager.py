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


class BlockingWebSocket(FakeWebSocket):
    """전송이 시작된 뒤 테스트가 허용할 때까지 멈추는 socket이다."""

    def __init__(self) -> None:
        super().__init__()
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def send_json(self, event: dict) -> None:
        self.concurrent_sends += 1
        self.max_concurrent_sends = max(self.max_concurrent_sends, self.concurrent_sends)
        self.started.set()
        try:
            await self.release.wait()
            self.sent.append(event)
        finally:
            self.concurrent_sends -= 1


class AcceptFailingWebSocket(FakeWebSocket):
    async def accept(self) -> None:
        raise RuntimeError("accept failed")


async def test_connect_accepts_socket_and_broadcast_delivers_topic_event():
    manager = WebSocketManager()
    websocket = FakeWebSocket()
    event = {"type": "task.event", "data": {"taskRunId": "task_1"}}

    await manager.connect(websocket)
    manager.subscribe(websocket, "task:task_1")
    await manager.broadcast(event, "task:task_1")

    assert websocket.accepted is True
    assert websocket.sent == [event]
    manager.disconnect(websocket)


async def test_connect_cleans_connection_state_when_accept_fails():
    manager = WebSocketManager()
    websocket = AcceptFailingWebSocket()

    try:
        await manager.connect(websocket)
    except RuntimeError as error:
        assert "accept failed" in str(error)
    else:
        raise AssertionError("accept failure was not raised")

    assert websocket not in manager._connections


async def test_broadcast_uses_all_topic_subscription():
    manager = WebSocketManager()
    websocket = FakeWebSocket()
    event = {"type": "system.notice"}

    await manager.connect(websocket)
    manager.subscribe(websocket, manager.topic_router.all_topic())
    await manager.broadcast(event, "task:task_1")

    assert websocket.sent == [event]
    manager.disconnect(websocket)


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
    manager.disconnect(fast_socket)


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
    manager.disconnect(websocket)


async def test_send_json_rejects_and_disconnects_when_outbound_queue_is_full():
    manager = WebSocketManager(max_queue_size=1)
    websocket = BlockingWebSocket()

    await manager.connect(websocket)
    manager.subscribe(websocket, "task:task_1")
    first_send = asyncio.create_task(manager.send_json(websocket, {"type": "first"}))
    await websocket.started.wait()
    queued_send = asyncio.create_task(manager.send_json(websocket, {"type": "queued"}))
    while manager._connections[websocket].queue.qsize() < 1:
        await asyncio.sleep(0)

    try:
        try:
            await manager.send_json(websocket, {"type": "overflow"})
        except RuntimeError as error:
            assert "outbound queue" in str(error)
        else:
            raise AssertionError("queue overflow did not reject the send")

        assert websocket not in manager.directory.get("task:task_1")
    finally:
        websocket.release.set()
        await asyncio.gather(first_send, queued_send, return_exceptions=True)
        manager.disconnect(websocket)
