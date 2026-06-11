from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import Settings, get_settings

# 토큰 검증 결과를 짧은 시간 캐싱해 폴링 요청마다 backend 왕복을 줄인다.
_TOKEN_CACHE_TTL_SECONDS = 30
_TOKEN_CACHE_MAX_SIZE = 512


@dataclass(slots=True)
class _CacheEntry:
    result: "BackendAuthVerifyResult"
    expires_at: float  # monotonic time


class BackendAuthVerifyError(RuntimeError):
    """backend JWT 검증 호출이나 응답 해석에 실패했음을 나타낸다."""


@dataclass(slots=True)
class BackendAuthVerifyResult:
    """backend JWT 검증 결과 중 AI 서버가 사용할 사용자 컨텍스트이다."""

    user_id: str
    workspace_key: str | None = None
    scopes: list[str] = field(default_factory=list)
    token_expires_at: str | None = None
    scope_expires_at: str | None = None


@dataclass(slots=True)
class BridgeTokenVerifyResult:
    """브릿지 토큰 검증 결과. backend /internal/bridge/auth/validate 응답을 그대로 담는다."""

    user_id: str
    device_id: str
    device_name: str


class BackendAuthClient:
    """backend 내부 인증 검증 API를 호출하는 client이다."""

    def __init__(self, *, settings: Settings | None = None, http_client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings or get_settings()
        self._http_client = http_client or httpx.AsyncClient()
        self._owns_http_client = http_client is None
        # (token, workspace_key) → _CacheEntry
        self._token_cache: dict[tuple[str, str | None], _CacheEntry] = {}
        self._cache_lock = asyncio.Lock()

    def _cache_get(self, token: str, workspace_key: str | None) -> BackendAuthVerifyResult | None:
        entry = self._token_cache.get((token, workspace_key))
        if entry is None:
            return None
        if time.monotonic() >= entry.expires_at:
            self._token_cache.pop((token, workspace_key), None)
            return None
        return entry.result

    def _cache_set(self, token: str, workspace_key: str | None, result: BackendAuthVerifyResult) -> None:
        # LRU 근사: 한도 초과 시 오래된 항목 제거
        if len(self._token_cache) >= _TOKEN_CACHE_MAX_SIZE:
            oldest_key = next(iter(self._token_cache))
            self._token_cache.pop(oldest_key, None)
        self._token_cache[(token, workspace_key)] = _CacheEntry(
            result=result,
            expires_at=time.monotonic() + _TOKEN_CACHE_TTL_SECONDS,
        )

    async def verify_access_token(self, access_token: str, *, workspace_key: str | None = None) -> BackendAuthVerifyResult:
        """사용자 access token을 backend에 위임 검증하고 검증 결과만 반환한다."""

        # 캐시 히트 시 backend 왕복 없이 즉시 반환한다.
        cached = self._cache_get(access_token, workspace_key)
        if cached is not None:
            return cached

        # AI는 사용자 JWT를 직접 신뢰하지 않고 backend 검증 결과만 신뢰한다.
        request_payload = {"accessToken": access_token}
        if workspace_key:
            request_payload["workspaceKey"] = workspace_key
        try:
            response = await self._http_client.post(
                self._settings.backend_auth_verify_url,
                json=request_payload,
                headers={"Authorization": f"Bearer {self._settings.internal_service_token or ''}"},
            )
        except httpx.HTTPError as exc:
            raise BackendAuthVerifyError("backend JWT 검증 요청 중 네트워크 오류가 발생했습니다.") from exc
        if response.status_code >= 400:
            raise BackendAuthVerifyError(f"backend JWT 검증 요청 실패: HTTP {response.status_code}")

        payload = self._read_json(response)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise BackendAuthVerifyError("backend JWT 검증 응답에 data가 없습니다.")

        user_id = self._required_user_id(data.get("userId"))

        result = BackendAuthVerifyResult(
            user_id=user_id,
            workspace_key=self._optional_str(data.get("workspaceKey")),
            scopes=self._parse_scopes(data.get("scope", data.get("scopes"))),
            token_expires_at=self._optional_str(data.get("jwtExpiresAt", data.get("tokenExpiresAt"))),
            scope_expires_at=self._optional_str(data.get("scopeExpiresAt")),
        )
        self._cache_set(access_token, workspace_key, result)
        return result

    async def verify_bridge_token(self, bridge_token: str) -> BridgeTokenVerifyResult:
        """브릿지 토큰을 backend에 위임 검증한다.

        브릿지 hello 메시지의 token 값을 그대로 넘기면 user/device 식별 결과만 받아온다.
        AI 서버 단일 공유 토큰 시절과 달리, AI 는 토큰 원본을 저장하지 않고 매 hello 마다 backend 검증을 거친다.
        """

        try:
            response = await self._http_client.post(
                self._settings.backend_bridge_auth_verify_url,
                json={"bridgeToken": bridge_token},
                headers={"Authorization": f"Bearer {self._settings.internal_service_token or ''}"},
            )
        except httpx.HTTPError as exc:
            raise BackendAuthVerifyError("backend 브릿지 토큰 검증 요청 중 네트워크 오류가 발생했습니다.") from exc
        if response.status_code >= 400:
            raise BackendAuthVerifyError(f"backend 브릿지 토큰 검증 요청 실패: HTTP {response.status_code}")

        payload = self._read_json(response)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise BackendAuthVerifyError("backend 브릿지 토큰 검증 응답에 data가 없습니다.")

        user_id = self._required_user_id(data.get("userId"))
        device_id = self._required_user_id(data.get("deviceId"))
        device_name_value = data.get("deviceName")
        device_name = device_name_value if isinstance(device_name_value, str) else ""

        return BridgeTokenVerifyResult(user_id=user_id, device_id=device_id, device_name=device_name)

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
