"""AI 서버 내부에서 backend 가 호출하는 브릿지 상태 조회 API.

backend 가 디바이스 목록을 응답할 때 "이 user 가 지금 정말 AI 서버에 WebSocket 으로 붙어있나"
를 확인하기 위해 호출한다. 인증은 HEYGENT_INTERNAL_SERVICE_TOKEN 으로 보호.
"""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


router = APIRouter(tags=["bridge-internal"])
_bearer_scheme = HTTPBearer(auto_error=False)


def _require_internal_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> None:
    settings = request.app.state.settings
    configured = (settings.internal_service_token or "").strip()
    if not configured:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="internal token not configured")
    provided = (credentials.credentials if credentials else "").strip()
    if not provided or not hmac.compare_digest(provided, configured):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid internal token")


@router.get(
    "/internal/bridge/online-users",
    summary="현재 AI 서버에 WebSocket 으로 붙어있는 브릿지 user_id 목록",
    dependencies=[Depends(_require_internal_token)],
)
def get_online_bridge_users(request: Request) -> dict[str, list[str]]:
    """BridgeSessionManager 의 살아있는 세션에서 user_id 만 뽑아 돌려준다.

    backend 가 GET /api/v1/bridge/devices 응답에 online 필드를 채우려고 호출한다.
    """

    manager = getattr(request.app.state, "bridge_session_manager", None)
    if manager is None:
        return {"userIds": []}
    sessions = getattr(manager, "_sessions_by_user", {}) or {}
    user_ids = [str(user_id) for user_id in sessions.keys()]
    return {"userIds": user_ids}
