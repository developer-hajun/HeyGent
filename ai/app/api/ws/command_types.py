from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable


class WebSocketCommandError(Exception):
    """command.error frame으로 변환할 수 있는 WebSocket protocol 오류다."""

    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


@dataclass(slots=True)
class WebSocketAuthContext:
    """인증된 WebSocket 연결이 살아 있는 동안만 유지되는 메모리 컨텍스트다.

    access_token은 backend 호출이 필요한 후속 command에서만 메모리로 참조할 수 있다.
    DB, event, projection, detail_json에는 절대 넣지 않는다.
    """

    user_id: str
    access_token: str
    workspace_key: str | None = None
    scopes: list[str] | None = None
    token_expires_at: str | None = None
    scope_expires_at: str | None = None


@dataclass(slots=True)
class WebSocketCommandContext:
    websocket: Any
    auth: WebSocketAuthContext
    gateway_session_id: str
    session_service: Any
    send_json: Callable[[dict[str, Any]], Awaitable[None]]
    background_tasks: set[asyncio.Task]
    after_response_callbacks: list[Callable[[], None]]


@dataclass(slots=True)
class WebSocketBackgroundContext:
    """연결 종료 뒤에도 실행될 수 있는 작업용 컨텍스트다.

    background task는 WebSocket close 이후까지 남을 수 있으므로 accessToken을 참조하지 않는다.
    """

    websocket: Any
    send_json: Callable[[dict[str, Any]], Awaitable[None]]
