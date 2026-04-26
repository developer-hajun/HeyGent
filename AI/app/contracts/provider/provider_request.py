from __future__ import annotations

from pydantic import Field

from app.contracts.common.base import ContractModel


class ProviderAuthRequest(ContractModel):
    """OAuth 시작에 필요한 최소 입력이다."""

    redirect_uri: str | None = Field(default=None, description="요청 시점에 덮어쓸 redirect URI")
    state: str | None = Field(default=None, description="클라이언트가 직접 관리할 state 값")
    force_oauth: bool = Field(default=True, description="기본 흐름으로 브라우저 OAuth 를 우선 시작할지 여부")


class ProviderCallbackRequest(ContractModel):
    """OAuth callback 단계의 auth code 와 state 를 전달한다."""

    code: str = Field(..., description="OAuth authorization code")
    state: str = Field(..., description="OAuth start 단계에서 발급받은 state")
