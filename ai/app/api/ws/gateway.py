from __future__ import annotations

import asyncio
import logging
from secrets import token_urlsafe
import time
from typing import Callable

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.clients.backend_auth import BackendAuthVerifyError, BackendAuthVerifyResult
from app.api.ws.commands import WebSocketAuthContext, WebSocketCommandContext, WebSocketCommandRouter
from app.api.ws.subscriptions import handle_subscription

router = APIRouter()
logger = logging.getLogger(__name__)
command_router = WebSocketCommandRouter()


class WebSocketAuthRateLimiter:
    """인증 실패가 반복되는 client를 짧은 시간 동안 차단하는 in-memory limiter다."""

    def __init__(self, *, max_failures: int, window_seconds: int, clock: Callable[[], float] = time.monotonic) -> None:
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self.clock = clock
        self._failures_by_client: dict[str, list[float]] = {}

    def allowed(self, client_key: str) -> bool:
        failures = self._recent_failures(client_key)
        return len(failures) < self.max_failures

    def record_failure(self, client_key: str) -> None:
        failures = self._recent_failures(client_key)
        failures.append(self.clock())
        self._failures_by_client[client_key] = failures

    def record_success(self, client_key: str) -> None:
        self._failures_by_client.pop(client_key, None)

    def _recent_failures(self, client_key: str) -> list[float]:
        threshold = self.clock() - self.window_seconds
        failures = [created_at for created_at in self._failures_by_client.get(client_key, []) if created_at >= threshold]
        self._failures_by_client[client_key] = failures
        return failures


def _websocket_origin_allowed(websocket: WebSocket) -> bool:
    """설정된 Origin 허용 목록과 요청 Origin 을 비교한다."""

    settings = websocket.app.state.settings
    allowed_origins = settings.ws_allowed_origins
    if not allowed_origins:
        return True

    origin = websocket.headers.get("origin")
    return origin in allowed_origins


def _websocket_client_key(websocket: WebSocket) -> str:
    client = websocket.client
    if client is None:
        return "unknown"
    return client.host or "unknown"


def build_websocket_auth_rate_limiter(settings) -> WebSocketAuthRateLimiter:
    return WebSocketAuthRateLimiter(
        max_failures=settings.ws_auth_rate_limit_max_failures,
        window_seconds=settings.ws_auth_rate_limit_window_seconds,
    )


def _client_message_action(message: dict) -> str | None:
    """제품 WebSocket 계약의 type 메시지를 내부 동작명으로 정규화한다."""

    message_type = message.get("type")
    if message_type == "auth.start":
        return "auth"
    if message_type == "ping":
        return "ping"
    if message_type == "subscribe.task":
        return "subscribe"
    if message_type == "subscribe.all":
        return "subscribe_all"
    return None


def _client_task_run_id(message: dict) -> str | None:
    """제품 WebSocket 계약의 camelCase TaskRun ID를 읽는다."""

    payload = message.get("payload")
    payload_dict = payload if isinstance(payload, dict) else {}
    task_run_id = message.get("taskRunId") or payload_dict.get("taskRunId") or payload_dict.get("task_run_id")
    if isinstance(task_run_id, str) and task_run_id:
        return task_run_id
    return None


async def _authenticate_first_message(websocket: WebSocket) -> WebSocketAuthContext | None:
    """인증 완료 전 상태 전이를 처리한다."""

    auth_client = websocket.app.state.backend_auth_client
    timeout_seconds = websocket.app.state.settings.ws_auth_first_message_timeout_seconds
    while True:
        try:
            message = await asyncio.wait_for(websocket.receive_json(), timeout=timeout_seconds)
        except TimeoutError:
            # 인증 전 첫 메시지를 무기한 기다리면 연결 슬롯을 점유할 수 있으므로 정책 위반으로 종료한다.
            await websocket.send_json({"type": "auth.timeout"})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None
        action = _client_message_action(message)
        if action == "ping":
            await websocket.send_json({"type": "pong"})
            continue
        if action != "auth":
            # 인증 전 구독을 허용하면 다른 사용자의 작업 이벤트를 엿볼 수 있으므로 즉시 거부한다.
            await websocket.send_json({"type": "auth.required"})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None

        payload = message.get("payload")
        payload_dict = payload if isinstance(payload, dict) else {}
        access_token = message.get("accessToken") or payload_dict.get("accessToken") or payload_dict.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            await websocket.send_json({"type": "auth.failed"})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None

        workspace_key = message.get("workspaceKey") or payload_dict.get("workspaceKey") or payload_dict.get("workspace_key")
        if workspace_key is not None and not isinstance(workspace_key, str):
            await websocket.send_json({"type": "auth.failed"})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None

        try:
            result: BackendAuthVerifyResult = await auth_client.verify_access_token(access_token, workspace_key=(workspace_key or None))
        except BackendAuthVerifyError:
            await websocket.send_json({"type": "auth.failed"})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None

        return WebSocketAuthContext(
            user_id=result.user_id,
            access_token=access_token,
            workspace_key=result.workspace_key,
            scopes=list(result.scopes),
            token_expires_at=result.token_expires_at,
            scope_expires_at=result.scope_expires_at,
        )


async def _handle_gateway_socket(websocket: WebSocket) -> None:
    manager = websocket.app.state.ws_manager
    session_service = websocket.app.state.session_service
    connection_registry = websocket.app.state.connection_registry
    session_id: str | None = None
    connection_id: str | None = None
    user_id: str | None = None
    send_lock = asyncio.Lock()
    background_tasks: set[asyncio.Task] = set()
    after_response_callbacks: list[Callable[[], None]] = []
    client_key = _websocket_client_key(websocket)
    rate_limiter = getattr(websocket.app.state, "ws_auth_rate_limiter", None)
    if not _websocket_origin_allowed(websocket):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    if rate_limiter is not None and not rate_limiter.allowed(client_key):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket)

    async def send_json(message: dict) -> None:
        async with send_lock:
            await websocket.send_json(message)

    try:
        auth_context = await _authenticate_first_message(websocket)
        if auth_context is None:
            if rate_limiter is not None:
                rate_limiter.record_failure(client_key)
            return

        # client query string의 userId/session_id는 위조 가능하므로 backend 검증 결과의 user_id만 세션 키로 사용한다.
        if rate_limiter is not None:
            rate_limiter.record_success(client_key)
        user_id = auth_context.user_id
        session_id = f"user:{user_id}"
        connection_id = token_urlsafe(24)
        try:
            await connection_registry.register_connection(
                connection_id=connection_id,
                user_id=user_id,
                session_id=session_id,
            )
        except Exception:
            # 인증은 맞더라도 연결 인덱스 저장 실패 시 fan-out/cleanup 기준이 깨지므로 성공 응답을 보내지 않는다.
            logger.exception("웹소켓 연결 레지스트리 등록에 실패했습니다.")
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            return

        auth_response = {"type": "auth.ok", "userId": user_id}
        if auth_context.workspace_key is not None:
            auth_response["workspaceKey"] = auth_context.workspace_key
        await send_json(auth_response)
        command_context = WebSocketCommandContext(
            websocket=websocket,
            auth=auth_context,
            gateway_session_id=session_id,
            session_service=session_service,
            send_json=send_json,
            background_tasks=background_tasks,
            after_response_callbacks=after_response_callbacks,
        )
        while True:
            message = await websocket.receive_json()
            action = _client_message_action(message)
            task_run_id = _client_task_run_id(message)
            if action == "subscribe" and task_run_id:
                await handle_subscription(
                    websocket,
                    session_service=session_service,
                    session_id=session_id,
                    authenticated_user_id=user_id,
                    task_run_id=task_run_id,
                    request_id=message.get("requestId"),
                    send_json=send_json,
                )
            elif action == "subscribe_all":
                # 전체 토픽 구독은 사용자별 소유권 검증을 우회하므로 제품 WebSocket에서는 열지 않는다.
                response = {
                    "type": "subscription.denied",
                    "taskRunId": "all",
                    "reason": "subscribe_all_disabled",
                }
                if message.get("requestId") is not None:
                    response["requestId"] = message.get("requestId")
                await send_json(response)
            elif action == "ping":
                try:
                    await connection_registry.touch_connection(
                        connection_id=connection_id,
                        user_id=user_id,
                        session_id=session_id,
                    )
                except Exception:
                    # heartbeat refresh 실패는 다음 ping/reconnect에서 복구할 수 있으므로 연결 자체는 유지한다.
                    logger.exception("웹소켓 연결 TTL 갱신에 실패했습니다.")
                await send_json({"type": "pong"})
            elif await command_router.handle(message, command_context):
                continue
            elif isinstance(message.get("type"), str):
                await command_router.send_unknown_command_error(message, command_context)
    except WebSocketDisconnect:
        pass
    finally:
        if session_id is not None:
            session_service.unsubscribe_all(session_id)
        if connection_id is not None and user_id is not None and session_id is not None:
            try:
                await connection_registry.unregister_connection(
                    connection_id=connection_id,
                    user_id=user_id,
                    session_id=session_id,
                )
            except Exception:
                # Redis cleanup 실패가 local WebSocketManager 정리를 막으면 같은 프로세스 fan-out 대상이 새므로 삼킨다.
                logger.exception("웹소켓 연결 레지스트리 정리에 실패했습니다.")
        manager.disconnect(websocket)


@router.websocket("/realtime/user/ws")
async def websocket_realtime_user(websocket: WebSocket) -> None:
    """제품 클라이언트가 사용하는 canonical WebSocket 경로다."""

    await _handle_gateway_socket(websocket)
