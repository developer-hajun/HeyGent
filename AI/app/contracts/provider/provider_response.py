from __future__ import annotations

from typing import Any

from pydantic import Field

from app.contracts.common.base import ContractModel


class ProviderHealthResponse(ContractModel):
    """Provider 상태 확인 응답이다."""

    provider_name: str
    healthy: bool
    configured: bool = False
    connected: bool = False
    auth_type: str | None = None
    detail: str
    missing_env: list[str] = Field(default_factory=list)
    scopes: list[str] = Field(default_factory=list)
    expires_at: str | None = None


class ProviderAuthResponse(ContractModel):
    """모델 프로바이더 인증 시작 또는 설정 상태 응답이다."""

    provider_name: str
    status: str
    detail: str
    authorization_url: str | None = None
    redirect_uri: str | None = None
    scopes: list[str] = Field(default_factory=list)
    state: str | None = None
    missing_env: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderConnectionResponse(ContractModel):
    """Provider 연결 완료 또는 연결 상태 응답이다."""

    provider_name: str
    status: str
    connected: bool
    detail: str
    scopes: list[str] = Field(default_factory=list)
    expires_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderGenerateResponse(ContractModel):
    """Provider 생성 응답 스키마다."""

    provider_name: str
    output_text: str
    usage: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
