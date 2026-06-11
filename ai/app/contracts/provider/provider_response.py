from __future__ import annotations

from typing import Any

from pydantic import Field

from app.contracts.common.base import ContractModel


class ProviderHealthResponse(ContractModel):
    """Provider 상태 확인 응답이다."""

    provider_name: str = Field(description="provider 이름입니다. provider(모델 제공자)는 OpenAI 같은 모델/API 공급자를 뜻합니다.")
    healthy: bool = Field(description="지금 모델 호출에 사용할 수 있으면 `true`입니다.")
    configured: bool = Field(default=False, description="필수 환경변수나 기본 설정이 준비되어 있으면 `true`입니다.")
    connected: bool = Field(default=False, description="OAuth/API key 등 인증 연결이 완료되어 있으면 `true`입니다.")
    auth_type: str | None = Field(default=None, description="인증 방식입니다. 예: `api_key`, `oauth`.")
    detail: str = Field(description="현재 상태를 사람이 읽기 쉽게 설명한 문장입니다.")
    missing_env: list[str] = Field(default_factory=list, description="설정되지 않은 필수 환경변수 목록입니다. 비어 있으면 설정 누락이 없습니다.")
    scopes: list[str] = Field(default_factory=list, description="OAuth 연결에서 허용된 권한 범위 목록입니다.")
    expires_at: str | None = Field(default=None, description="OAuth access token 만료 시각입니다. API key 방식이면 `null`일 수 있습니다.")


class ProviderAuthResponse(ContractModel):
    """모델 프로바이더 인증 시작 또는 설정 상태 응답이다."""

    provider_name: str = Field(description="인증을 시작한 provider 이름입니다.")
    status: str = Field(description="인증 시작 결과 상태입니다. 예: `ready`, `missing_env`, `oauth_required`.")
    detail: str = Field(description="다음에 무엇을 해야 하는지 설명하는 문장입니다.")
    authorization_url: str | None = Field(default=None, description="브라우저에서 열 OAuth 인증 URL입니다. API key 방식이면 `null`일 수 있습니다.")
    redirect_uri: str | None = Field(default=None, description="OAuth 완료 후 돌아올 redirect URI입니다.")
    scopes: list[str] = Field(default_factory=list, description="요청할 OAuth 권한 범위입니다.")
    state: str | None = Field(default=None, description="callback 검증용 state 값입니다.")
    missing_env: list[str] = Field(default_factory=list, description="인증 시작 전에 필요한데 빠진 환경변수 목록입니다.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="provider별 추가 정보입니다. 모르는 키는 무시해도 됩니다.")


class ProviderConnectionResponse(ContractModel):
    """Provider 연결 완료 또는 연결 상태 응답이다."""

    provider_name: str = Field(description="연결 상태를 변경한 provider 이름입니다.")
    status: str = Field(description="연결 결과 상태입니다. 예: `connected`, `refreshed`, `disconnected`.")
    connected: bool = Field(description="현재 provider 인증이 연결되어 있으면 `true`입니다.")
    detail: str = Field(description="연결 결과를 사람이 읽기 쉽게 설명한 문장입니다.")
    scopes: list[str] = Field(default_factory=list, description="현재 연결에 허용된 OAuth 권한 범위입니다.")
    expires_at: str | None = Field(default=None, description="OAuth access token 만료 시각입니다.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="provider별 추가 연결 정보입니다. 모르는 키는 무시해도 됩니다.")
