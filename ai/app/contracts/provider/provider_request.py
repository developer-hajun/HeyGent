from __future__ import annotations

from pydantic import Field

from app.contracts.common.base import ContractModel


class ProviderAuthRequest(ContractModel):
    """OAuth 시작에 필요한 최소 입력이다."""

    redirect_uri: str | None = Field(default=None, description="OAuth 완료 후 돌아올 redirect URI입니다. 비워 두면 서버 설정값을 사용합니다.")
    state: str | None = Field(default=None, description="OAuth 위조 요청을 막기 위한 state 값입니다. 직접 넣지 않으면 provider가 생성합니다.")
    force_oauth: bool = Field(default=True, description="`true`이면 브라우저 OAuth 흐름을 우선 시작합니다. API key provider는 설정 상태만 반환할 수 있습니다.")


class ProviderCallbackRequest(ContractModel):
    """OAuth callback 단계의 auth code 와 state 를 전달한다."""

    code: str = Field(..., description="OAuth provider가 callback으로 돌려준 authorization code(토큰 교환용 일회성 코드)입니다.")
    state: str = Field(..., description="`/auth` 단계에서 발급받은 state 값입니다. 요청 위조 방지와 callback 검증에 사용합니다.")
