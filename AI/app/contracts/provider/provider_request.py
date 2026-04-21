from __future__ import annotations

from typing import Any

from pydantic import Field

from app.contracts.common.base import ContractModel


class ProviderGenerateRequest(ContractModel):
    """Model Provider 호출 입력 스키마다."""

    provider_name: str = Field(..., description="호출할 provider 이름")
    prompt: str = Field(..., description="생성 요청 프롬프트")
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderAuthRequest(ContractModel):
    """OAuth 시작에 필요한 최소 입력이다."""

    redirect_uri: str | None = Field(default=None, description="요청 시점에 덮어쓸 redirect URI")
    state: str | None = Field(default=None, description="클라이언트가 직접 관리할 state 값")
