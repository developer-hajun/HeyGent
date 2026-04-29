from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


swagger_bearer_auth = HTTPBearer(
    auto_error=False,
    scheme_name="BackendAccessToken",
    description="backend /api/v1/auth/dev-login 에서 받은 accessToken 을 입력한다.",
)


async def document_bearer_auth(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(swagger_bearer_auth)] = None,
) -> None:
    """Swagger UI에 Bearer 인증 입력창을 노출하기 위한 문서용 dependency다.

    실제 권한 검증은 각 HTTP handler의 authenticate_http_user가 수행한다.
    """

    return None
