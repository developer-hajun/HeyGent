from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.clients.backend_auth import BackendAuthClient, BackendAuthVerifyError, BridgeTokenVerifyResult


router = APIRouter()
logger = logging.getLogger(__name__)

# 브릿지 hello 메시지를 처음 받을 때까지 기다릴 시간(초).
# 너무 길게 잡으면 연결 슬롯을 무한히 점유할 수 있으므로 짧게 둔다.
BRIDGE_HELLO_TIMEOUT_SECONDS = 5.0


async def _await_bridge_hello(websocket: WebSocket) -> tuple[dict[str, Any], BridgeTokenVerifyResult] | None:
    """브릿지 첫 메시지(`bridge.hello`)를 읽고 토큰을 backend 에 위임 검증한다.

    검증 성공 시 hello 메시지와 backend 검증 결과(user/device) 를 반환한다.
    인증 실패면 정책 위반으로 즉시 종료한다.
    """

    try:
        message = await asyncio.wait_for(websocket.receive_json(), timeout=BRIDGE_HELLO_TIMEOUT_SECONDS)
    except TimeoutError:
        await websocket.send_json({"type": "bridge.error", "reason": "hello_timeout"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    if not isinstance(message, dict) or message.get("type") != "bridge.hello":
        await websocket.send_json({"type": "bridge.error", "reason": "expected_bridge_hello"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    provided_token = str(message.get("token") or "").strip()
    if not provided_token:
        await websocket.send_json({"type": "bridge.error", "reason": "missing_token"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    # backend 에 검증을 위임한다. internal_service_token 이 비어있으면 backend 가 401 로 거절하므로
    # AI 서버 단에서 별도로 가드할 필요는 없다.
    settings = websocket.app.state.settings
    backend_client: BackendAuthClient | None = getattr(websocket.app.state, "backend_auth_client", None)
    owns_client = backend_client is None
    if backend_client is None:
        backend_client = BackendAuthClient(settings=settings)

    try:
        verification = await backend_client.verify_bridge_token(provided_token)
    except BackendAuthVerifyError as exc:
        logger.warning("브릿지 토큰 검증 실패: %s", exc)
        await websocket.send_json({"type": "bridge.error", "reason": "invalid_token"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    finally:
        if owns_client:
            await backend_client.aclose()

    return message, verification


@router.websocket("/internal/bridge/ws")
async def websocket_bridge(websocket: WebSocket) -> None:
    """로컬 브릿지 프로그램 전용 WebSocket 엔드포인트이다.

    hello 토큰을 backend 로 검증해 user_id / device_id 를 얻고, user 별 슬롯에 등록한다.
    """

    await websocket.accept()

    hello_result = await _await_bridge_hello(websocket)
    if hello_result is None:
        return
    hello, verification = hello_result

    workspace_root = str(hello.get("workspace_root") or "").strip() or None
    manager = websocket.app.state.bridge_session_manager
    session = await manager.register(
        websocket,
        user_id=verification.user_id,
        device_id=verification.device_id,
        device_name=verification.device_name,
        workspace_root=workspace_root,
    )

    await websocket.send_json(
        {
            "type": "bridge.ack",
            "session_id": session.session_id,
            "user_id": verification.user_id,
            "device_name": verification.device_name,
        }
    )

    try:
        while True:
            message = await websocket.receive_json()
            if not isinstance(message, dict):
                continue
            message_type = message.get("type")
            if message_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            if message_type == "tool.result":
                call_id = str(message.get("call_id") or "").strip()
                result = message.get("result")
                if not call_id or not isinstance(result, dict):
                    logger.warning("브릿지 tool.result 형식이 올바르지 않습니다: %s", message)
                    continue
                # 동기 run_call에서 기다리고 있던 Future에 결과를 꽂아 준다.
                manager.deliver_tool_result(session_id=session.session_id, call_id=call_id, result=result)
                continue
            logger.debug("브릿지 메시지 수신: type=%s", message_type)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("브릿지 WebSocket 처리 중 예외 발생")
    finally:
        await manager.unregister(session.session_id)
