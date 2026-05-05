from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from secrets import token_urlsafe
from typing import Any

from fastapi import WebSocket


logger = logging.getLogger(__name__)


# 브릿지가 도구 실행 결과를 보내기까지 기다릴 기본 시간(초).
# 단계 2에서는 짧은 명령(whoami, hostname 등)만 다루므로 충분히 짧게 둔다.
DEFAULT_TOOL_INVOKE_TIMEOUT_SECONDS = 30.0


@dataclass(slots=True)
class BridgeSession:
    """현재 연결된 로컬 브릿지 한 개의 상태이다.

    PoC 단계 2에서는 hello/ack 외에 tool.invoke / tool.result 흐름을 추가한다.
    pending_calls는 브릿지에 보낸 도구 호출 중 결과를 기다리는 Future를 보관한다.
    """

    session_id: str
    websocket: WebSocket
    workspace_root: str | None = None
    connected_at: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    # call_id -> Future. 동기 컨텍스트에서 결과를 set 할 수 있도록 asyncio.Future 그대로 사용.
    pending_calls: dict[str, asyncio.Future] = field(default_factory=dict)


class BridgeSessionManager:
    """AI 서버 프로세스 안에서 현재 연결된 로컬 브릿지를 추적하고,
    도구 호출을 그 브릿지로 위임한다.

    PoC 범위에서는 동시에 1대의 브릿지만 허용한다 (단일 유저 가정).
    이벤트 루프 참조를 lifespan에서 주입받아, run_call 같은 동기 컨텍스트에서도
    브릿지로 위임할 수 있게 한다.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._session: BridgeSession | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """동기 컨텍스트에서 비동기 위임 호출을 가능하게 하기 위해 메인 이벤트 루프를 보관한다."""

        self._loop = loop

    async def register(self, websocket: WebSocket, *, workspace_root: str | None) -> BridgeSession:
        """새 브릿지 연결을 단일 슬롯에 등록한다.

        이미 다른 브릿지가 연결돼 있으면 기존 연결을 정리하고 새 것을 받는다.
        PoC 단계에서는 "마지막에 들어온 브릿지가 우선"이라는 단순 정책으로 시작한다.
        """

        async with self._lock:
            previous = self._session
            session = BridgeSession(
                session_id=token_urlsafe(16),
                websocket=websocket,
                workspace_root=workspace_root,
                connected_at=asyncio.get_event_loop().time(),
            )
            self._session = session

        if previous is not None:
            # 기존 세션이 가진 pending Future들도 같이 실패 처리한다.
            for call_id, future in list(previous.pending_calls.items()):
                if not future.done():
                    future.set_exception(BridgeDisconnected(f"브릿지가 새 연결로 교체되어 호출 {call_id}가 취소됐습니다"))
            try:
                await previous.websocket.close()
            except Exception:
                logger.exception("이전 브릿지 WebSocket 정리에 실패했습니다.")

        logger.info("브릿지 연결됨: session_id=%s, workspace_root=%s", session.session_id, workspace_root)
        return session

    async def unregister(self, session_id: str) -> None:
        """브릿지 연결이 끊겼을 때 등록 슬롯을 비운다.

        다른 브릿지가 이미 들어와서 슬롯을 차지한 경우에는 그대로 둔다.
        끊긴 세션의 pending Future는 모두 실패 처리한다.
        """

        async with self._lock:
            if self._session is None or self._session.session_id != session_id:
                return
            session = self._session
            self._session = None

        for call_id, future in list(session.pending_calls.items()):
            if not future.done():
                future.set_exception(BridgeDisconnected(f"브릿지 연결이 끊겨 호출 {call_id}가 취소됐습니다"))
        session.pending_calls.clear()
        logger.info("브릿지 연결 해제됨: session_id=%s", session_id)

    def is_alive(self) -> bool:
        """현재 살아있는 브릿지 연결이 있는지 빠르게 확인한다.

        run_call 분기에서 이 값으로 위임 가능 여부를 판정한다.
        """

        return self._session is not None

    def current_session(self) -> BridgeSession | None:
        return self._session

    def deliver_tool_result(self, *, call_id: str, result: dict[str, Any]) -> None:
        """브릿지가 보낸 tool.result를 기다리고 있던 Future에 전달한다.

        WebSocket 수신 루프(브릿지 gateway)에서 호출한다.
        """

        session = self._session
        if session is None:
            return
        future = session.pending_calls.pop(call_id, None)
        if future is None:
            logger.warning("브릿지 응답에 대응하는 pending 호출이 없습니다: call_id=%s", call_id)
            return
        if not future.done():
            future.set_result(result)

    def execute_sync(
        self,
        *,
        name: str,
        args: dict[str, Any],
        timeout_seconds: float = DEFAULT_TOOL_INVOKE_TIMEOUT_SECONDS,
    ) -> dict[str, Any]:
        """동기 컨텍스트(LocalToolRuntime.run_call)에서 브릿지로 도구 호출을 위임한다.

        내부적으로 메인 이벤트 루프에 코루틴을 던지고 결과를 기다린다.
        타임아웃이나 미연결은 예외 대신 호출자에게 명확한 dict로 돌려주도록 상위에서 처리한다.
        """

        loop = self._loop
        if loop is None:
            raise BridgeNotReady("브릿지 이벤트 루프가 아직 바인딩되지 않았습니다")

        future = asyncio.run_coroutine_threadsafe(
            self._invoke(name=name, args=args, timeout_seconds=timeout_seconds),
            loop,
        )
        return future.result(timeout=timeout_seconds + 5.0)

    async def _invoke(
        self,
        *,
        name: str,
        args: dict[str, Any],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        """브릿지에 tool.invoke를 보내고 tool.result를 기다린다 (이벤트 루프 안에서 실행)."""

        session = self._session
        if session is None:
            raise BridgeDisconnected("브릿지가 연결돼 있지 않습니다")

        call_id = token_urlsafe(12)
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        session.pending_calls[call_id] = future

        payload = {
            "type": "tool.invoke",
            "call_id": call_id,
            "name": name,
            "args": args,
            "timeout_seconds": timeout_seconds,
        }
        try:
            await session.websocket.send_text(json.dumps(payload, ensure_ascii=False))
        except Exception as exc:
            session.pending_calls.pop(call_id, None)
            raise BridgeDisconnected(f"브릿지로 tool.invoke 전송 실패: {exc}") from exc

        try:
            return await asyncio.wait_for(future, timeout=timeout_seconds)
        except asyncio.TimeoutError as exc:
            session.pending_calls.pop(call_id, None)
            raise BridgeTimeout(f"브릿지 응답 대기 시간({timeout_seconds}s)을 초과했습니다") from exc


class BridgeError(RuntimeError):
    """브릿지 위임 호출에서 발생하는 모든 오류의 공통 부모."""


class BridgeNotReady(BridgeError):
    """이벤트 루프가 아직 바인딩되지 않은 상태에서 호출됐을 때."""


class BridgeDisconnected(BridgeError):
    """브릿지가 연결돼 있지 않거나 호출 중 끊겼을 때."""


class BridgeTimeout(BridgeError):
    """브릿지가 시간 안에 응답하지 않았을 때."""
