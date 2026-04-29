from __future__ import annotations

from fastapi import HTTPException, Request

from app.clients.backend_auth import BackendAuthVerifyError, BackendAuthVerifyResult


async def authenticate_http_user(request: Request) -> BackendAuthVerifyResult | None:
    """제품 HTTP API에서 backend 검증 결과를 실행 권한 기준으로 사용한다."""

    authorization = str(request.headers.get("authorization") or "").strip()
    if not authorization:
        # legacy SQLite 테스트 런타임은 기존 단위 테스트와 CLI 호환을 위해 인증 없는 호출을 유지한다.
        if getattr(request.app.state.settings, "allow_sqlite_legacy", False):
            return None
        raise HTTPException(status_code=401, detail="authorization required")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="bearer token required")

    try:
        return await request.app.state.backend_auth_client.verify_access_token(token.strip())
    except BackendAuthVerifyError as error:
        raise HTTPException(status_code=401, detail="invalid authorization") from error


def ensure_owner(user: BackendAuthVerifyResult | None, owner_key: str | None) -> None:
    """인증 사용자가 있으면 row owner와 반드시 일치해야 한다."""

    if user is None:
        return
    if str(owner_key or "") != str(user.user_id):
        raise HTTPException(status_code=403, detail="forbidden")
