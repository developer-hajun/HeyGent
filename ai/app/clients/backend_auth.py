from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import Settings, get_settings


class BackendAuthVerifyError(RuntimeError):
    """backend JWT 검증 호출이나 응답 해석에 실패했음을 나타낸다."""


@dataclass(slots=True)
class BackendAuthVerifyResult:
    """backend JWT 검증 결과 중 AI 서버가 사용할 사용자 컨텍스트이다."""

    user_id: str
    workspace_key: str | None = None
    scopes: list[str] = field(default_factory=list)
    token_expires_at: str | None = None


class BackendAuthClient:
    """backend 내부 인증 검증 API를 호출하는 client이다."""

    def __init__(self, *, settings: Settings | None = None, http_client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings or get_settings()
        self._http_client = http_client or httpx.AsyncClient()
        self._owns_http_client = http_client is None

    async def verify_access_token(self, access_token: str) -> BackendAuthVerifyResult:
        """사용자 access token을 backend에 위임 검증하고 검증 결과만 반환한다."""

        # AI는 사용자 JWT를 직접 신뢰하지 않고 backend 검증 결과만 신뢰한다.
        response = await self._http_client.post(
            self._settings.backend_auth_verify_url,
            json={"accessToken": access_token},
            headers={"X-Internal-Service-Token": self._settings.internal_service_token or ""},
        )
        if response.status_code >= 400:
            raise BackendAuthVerifyError(f"backend JWT 검증 요청 실패: HTTP {response.status_code}")

        payload = self._read_json(response)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise BackendAuthVerifyError("backend JWT 검증 응답에 data가 없습니다.")

        user_id = self._required_user_id(data.get("userId"))

        return BackendAuthVerifyResult(
            user_id=user_id,
            workspace_key=self._optional_str(data.get("workspaceKey")),
            scopes=self._parse_scopes(data.get("scopes")),
            token_expires_at=self._optional_str(data.get("tokenExpiresAt")),
        )

    async def aclose(self) -> None:
        """client가 생성한 HTTP 세션만 닫는다."""

        if self._owns_http_client:
            await self._http_client.aclose()

    def _read_json(self, response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise BackendAuthVerifyError("backend JWT 검증 응답이 JSON 형식이 아닙니다.") from exc
        if not isinstance(payload, dict):
            raise BackendAuthVerifyError("backend JWT 검증 응답 wrapper가 객체가 아닙니다.")
        return payload

    def _parse_scopes(self, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list) or not all(isinstance(scope, str) for scope in value):
            raise BackendAuthVerifyError("backend JWT 검증 응답의 scopes 형식이 올바르지 않습니다.")
        return value

    def _optional_str(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        raise BackendAuthVerifyError("backend JWT 검증 응답 필드 형식이 올바르지 않습니다.")

    def _required_user_id(self, value: Any) -> str:
        # backend는 Java Long 값을 JSON 숫자로 내려주므로 AI 내부에서는 문자열 ID로 정규화한다.
        if isinstance(value, int) and not isinstance(value, bool):
            return str(value)
        if isinstance(value, str) and value:
            return value
        raise BackendAuthVerifyError("backend JWT 검증 응답에 userId가 없습니다.")
