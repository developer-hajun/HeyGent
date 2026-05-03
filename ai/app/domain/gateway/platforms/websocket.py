from __future__ import annotations

import asyncio

from fastapi import WebSocket

from app.domain.gateway.routing.channel_directory import ChannelDirectory
from app.domain.gateway.routing.topic_router import TopicRouter


class WebSocketManager:
    """Websocket transport adapter for gateway delivery."""

    def __init__(
        self,
        directory: ChannelDirectory | None = None,
        topic_router: TopicRouter | None = None,
        *,
        send_timeout_seconds: float = 5.0,
    ) -> None:
        self.directory = directory or ChannelDirectory()
        self.topic_router = topic_router or TopicRouter()
        self.send_timeout_seconds = send_timeout_seconds
        # 같은 브라우저 WebSocket으로 command 응답과 TaskRun 이벤트가 동시에 나갈 수 있다.
        # Starlette WebSocket write는 병렬 호출에 취약하므로 연결 단위 lock으로 순서를 고정한다.
        self._send_locks: dict[WebSocket, asyncio.Lock] = {}

    async def connect(self, websocket: WebSocket) -> None:
        self._send_locks.setdefault(websocket, asyncio.Lock())
        await websocket.accept()

    def disconnect(self, websocket: WebSocket) -> None:
        self.directory.discard(websocket)
        self._send_locks.pop(websocket, None)

    def subscribe(self, websocket: WebSocket, topic: str) -> None:
        self.directory.add(topic, websocket)

    async def send_json(self, websocket: WebSocket, event: dict, *, timeout_seconds: float | None = None) -> None:
        """연결 단위로 안전하게 JSON frame을 전송한다."""

        lock = self._send_locks.setdefault(websocket, asyncio.Lock())
        timeout = self.send_timeout_seconds if timeout_seconds is None else timeout_seconds
        async with lock:
            await asyncio.wait_for(websocket.send_json(event), timeout=timeout)

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
