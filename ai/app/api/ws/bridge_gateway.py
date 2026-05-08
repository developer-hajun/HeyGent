from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status


router = APIRouter()
logger = logging.getLogger(__name__)

# 브릿지 hello 메시지를 처음 받을 때까지 기다릴 시간(초).
# 너무 길게 잡으면 연결 슬롯을 무한히 점유할 수 있으므로 짧게 둔다.
BRIDGE_HELLO_TIMEOUT_SECONDS = 5.0


async def _await_bridge_hello(websocket: WebSocket) -> dict[str, Any] | None:
    """브릿지 첫 메시지(`bridge.hello`)를 읽고 토큰을 검증한다.

    인증 토큰이 일치하지 않으면 정책 위반으로 즉시 종료한다.
    PoC 단계에서는 단일 공유 토큰을 .env에서 읽어 비교한다.
    """

    settings = websocket.app.state.settings
    expected_token = (settings.bridge_token or "").strip()
    if not expected_token:
        # 서버에 토큰이 설정돼 있지 않으면 어떤 브릿지든 받지 않는다.
        # PoC라도 인증 미설정 상태로 외부 연결을 받지 않는 게 안전하다.
        await websocket.send_json({"type": "bridge.error", "reason": "bridge_token_not_configured"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

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
    if provided_token != expected_token:
        await websocket.send_json({"type": "bridge.error", "reason": "invalid_token"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    return message


@router.websocket("/internal/bridge/ws")
async def websocket_bridge(websocket: WebSocket) -> None:
    """로컬 브릿지 프로그램 전용 WebSocket 엔드포인트이다.

    PoC 단계 1에서는 hello 수신, 등록, ping/pong, 연결 해제만 처리한다.
    tool.invoke / tool.result 흐름은 단계 2에서 확장한다.
    """

    await websocket.accept()

    hello = await _await_bridge_hello(websocket)
    if hello is None:
        return

    workspace_root = str(hello.get("workspace_root") or "").strip() or None
    manager = websocket.app.state.bridge_session_manager
    session = await manager.register(websocket, workspace_root=workspace_root)

    await websocket.send_json(
        {
            "type": "bridge.ack",
            "session_id": session.session_id,
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
                manager.deliver_tool_result(call_id=call_id, result=result)
                continue
            logger.debug("브릿지 메시지 수신: type=%s", message_type)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("브릿지 WebSocket 처리 중 예외 발생")
    finally:
        await manager.unregister(session.session_id)
