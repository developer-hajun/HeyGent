from __future__ import annotations

import asyncio
from dataclasses import dataclass

from fastapi import WebSocket

from app.domain.gateway.routing.channel_directory import ChannelDirectory
from app.domain.gateway.routing.topic_router import TopicRouter


@dataclass(slots=True)
class _OutboundFrame:
    """연결별 전송 queue 안에서 실제 send 결과를 기다리기 위한 내부 frame이다."""

    event: dict
    future: asyncio.Future[None]
    timeout_seconds: float


@dataclass(slots=True)
class _ConnectionState:
    queue: asyncio.Queue[_OutboundFrame]
    pump_task: asyncio.Task


class WebSocketManager:
    """Websocket transport adapter for gateway delivery."""

    def __init__(
        self,
        directory: ChannelDirectory | None = None,
        topic_router: TopicRouter | None = None,
        *,
        send_timeout_seconds: float = 5.0,
        max_queue_size: int = 200,
    ) -> None:
        self.directory = directory or ChannelDirectory()
        self.topic_router = topic_router or TopicRouter()
        self.send_timeout_seconds = send_timeout_seconds
        self.max_queue_size = max_queue_size
        # 같은 브라우저 WebSocket으로 command 응답과 TaskRun 이벤트가 동시에 나갈 수 있다.
        # 연결별 queue pump(전송 전담 작업) 하나만 실제 send_json을 호출하게 만들어 frame 순서를 고정한다.
        self._connections: dict[WebSocket, _ConnectionState] = {}

    async def connect(self, websocket: WebSocket) -> None:
        self._ensure_connection_state(websocket)
        try:
            await websocket.accept()
        except Exception:
            # handshake가 실패하면 아직 endpoint finally에 진입하지 못했을 수 있으므로 여기서 pump를 정리한다.
            self.disconnect(websocket)
            raise

    def disconnect(self, websocket: WebSocket) -> None:
        self.directory.discard(websocket)
        state = self._connections.pop(websocket, None)
        if state is None:
            return
        if state.pump_task is not asyncio.current_task():
            state.pump_task.cancel()
        self._reject_queued_frames(state, RuntimeError("WebSocket connection closed"))

    def subscribe(self, websocket: WebSocket, topic: str) -> None:
        self.directory.add(topic, websocket)

    async def send_json(self, websocket: WebSocket, event: dict, *, timeout_seconds: float | None = None) -> None:
        """연결 단위 outbound queue를 거쳐 JSON frame을 전송한다."""

        timeout = self.send_timeout_seconds if timeout_seconds is None else timeout_seconds
        state = self._connections.get(websocket)
        if state is None:
            raise RuntimeError("WebSocket connection is not registered")
        loop = asyncio.get_running_loop()
        future: asyncio.Future[None] = loop.create_future()
        frame = _OutboundFrame(event=event, future=future, timeout_seconds=timeout)
        try:
            state.queue.put_nowait(frame)
        except asyncio.QueueFull as error:
            # 소비자가 따라오지 못하는 연결은 계속 쌓아 두면 전체 프로세스 메모리를 압박한다.
            # 해당 연결만 정리하고, 다른 사용자/세션 fan-out은 계속 진행한다.
            self.disconnect(websocket)
            raise RuntimeError("WebSocket outbound queue is full") from error
        await future

    async def broadcast(self, event: dict, topic: str) -> None:
        target_set = self.directory.get(topic)
        target_set.update(self.directory.get(self.topic_router.all_topic()))
        targets = list(target_set)
        if not targets:
            return

        # 한 느린 client가 같은 topic의 다른 client까지 막지 않게 socket별 전송을 분리한다.
        results = await asyncio.gather(*(self._send_or_stale(websocket, event) for websocket in targets))
        for websocket, is_stale in zip(targets, results, strict=True):
            if is_stale:
                self.disconnect(websocket)

    async def _send_or_stale(self, websocket: WebSocket, event: dict) -> bool:
        try:
            await self.send_json(websocket, event)
            return False
        except Exception:
            return True

    def _ensure_connection_state(self, websocket: WebSocket) -> _ConnectionState:
        state = self._connections.get(websocket)
        if state is not None:
            return state
        queue: asyncio.Queue[_OutboundFrame] = asyncio.Queue(maxsize=self.max_queue_size)
        state = _ConnectionState(
            queue=queue,
            pump_task=asyncio.create_task(self._pump_outbound_frames(websocket, queue)),
        )
        self._connections[websocket] = state
        return state

    async def _pump_outbound_frames(self, websocket: WebSocket, queue: asyncio.Queue[_OutboundFrame]) -> None:
        current_frame: _OutboundFrame | None = None
        try:
            while True:
                frame = await queue.get()
                current_frame = frame
                try:
                    await asyncio.wait_for(websocket.send_json(frame.event), timeout=frame.timeout_seconds)
                    if not frame.future.done():
                        frame.future.set_result(None)
                except asyncio.CancelledError:
                    if not frame.future.done():
                        frame.future.set_exception(RuntimeError("WebSocket connection closed"))
                    raise
                except Exception as error:
                    if not frame.future.done():
                        frame.future.set_exception(error)
                    self.disconnect(websocket)
                    return
                finally:
                    current_frame = None
                    queue.task_done()
        except asyncio.CancelledError:
            if current_frame is not None and not current_frame.future.done():
                current_frame.future.set_exception(RuntimeError("WebSocket connection closed"))
            return

    def _reject_queued_frames(self, state: _ConnectionState, error: Exception) -> None:
        while True:
            try:
                frame = state.queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            if not frame.future.done():
                frame.future.set_exception(error)
            state.queue.task_done()
