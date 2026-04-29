from __future__ import annotations

import logging
from secrets import token_urlsafe

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.clients.backend_auth import BackendAuthVerifyError, BackendAuthVerifyResult
from app.api.ws.subscriptions import handle_subscription

router = APIRouter()
logger = logging.getLogger(__name__)


async def _authenticate_first_message(websocket: WebSocket) -> BackendAuthVerifyResult | None:
    """인증 완료 전 상태 전이를 처리한다."""

    auth_client = websocket.app.state.backend_auth_client
    while True:
        message = await websocket.receive_json()
        action = message.get("action")
        if action == "ping":
            await websocket.send_json({"type": "pong"})
            continue
        if action != "auth":
            # 인증 전 구독을 허용하면 다른 사용자의 작업 이벤트를 엿볼 수 있으므로 즉시 거부한다.
            await websocket.send_json({"type": "auth.required"})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None

        access_token = message.get("accessToken")
        if not isinstance(access_token, str) or not access_token:
            await websocket.send_json({"type": "auth.failed"})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None

        try:
            result = await auth_client.verify_access_token(access_token)
        except BackendAuthVerifyError:
            await websocket.send_json({"type": "auth.failed"})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None

        return result


async def _handle_gateway_socket(websocket: WebSocket) -> None:
    manager = websocket.app.state.ws_manager
    session_service = websocket.app.state.session_service
    connection_registry = websocket.app.state.connection_registry
    session_id: str | None = None
    connection_id: str | None = None
    user_id: str | None = None
    await manager.connect(websocket)
    try:
        auth_result = await _authenticate_first_message(websocket)
        if auth_result is None:
            return

        # client query string의 userId/session_id는 위조 가능하므로 backend 검증 결과의 user_id만 세션 키로 사용한다.
        user_id = auth_result.user_id
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

        await websocket.send_json({"type": "auth.ok", "userId": user_id})
        while True:
            message = await websocket.receive_json()
            action = message.get("action")
            if action == "subscribe" and message.get("task_run_id"):
                await handle_subscription(
                    websocket,
                    session_service=session_service,
                    session_id=session_id,
                    task_run_id=message["task_run_id"],
                )
            elif action == "subscribe_all":
                session_service.subscribe_all(session_id=session_id, websocket=websocket)
                await websocket.send_json({"type": "subscribed", "task_run_id": "all"})
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
                await websocket.send_json({"type": "pong"})
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


@router.websocket("/gateway/ws")
async def websocket_gateway(websocket: WebSocket) -> None:
    """권장 WebSocket 경로다.

    HTTP 표면이 `/api/v1/...` 로 정리된 뒤에는,
    WebSocket 도 단순 `/ws` 보다 `/gateway/ws` 가 역할을 더 명확히 보여 준다.
    """

    await _handle_gateway_socket(websocket)


@router.websocket("/ws")
async def websocket_gateway_legacy(websocket: WebSocket) -> None:
    """이전 테스트나 임시 클라이언트를 위한 호환 경로다."""

    await _handle_gateway_socket(websocket)
