from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.api.deps.http_auth import authenticate_http_user

router = APIRouter(prefix="/fcm", tags=["fcm"])

# In-memory 저장 (재시작 시 초기화).
# 운영 환경에서는 Redis/DB로 교체 권장.
_fcm_tokens: dict[str, str] = {}  # user_id → fcm_token


class FcmTokenRequest(BaseModel):
    token: str


@router.post("/token", summary="FCM 디바이스 토큰 등록/갱신")
async def register_fcm_token(request: Request, payload: FcmTokenRequest) -> dict:
    """모바일 앱에서 FCM 토큰이 발급/갱신될 때 호출한다."""
    user = await authenticate_http_user(request)
    _fcm_tokens[str(user.user_id)] = payload.token
    return {"ok": True}


def get_fcm_token(user_id: str) -> str | None:
    """내부용: user_id로 등록된 FCM 토큰을 조회한다."""
    return _fcm_tokens.get(str(user_id))
