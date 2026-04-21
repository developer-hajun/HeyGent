from __future__ import annotations

from urllib.parse import urlencode

from app.contracts.provider.provider_response import ProviderAuthResponse, ProviderGenerateResponse, ProviderHealthResponse
from app.core.config import Settings
from app.core.utils.ids import new_id
from app.domain.providers.base import BaseProvider


class OpenAIOAuthProvider(BaseProvider):
    """OpenAI OAuth 기반 모델 프로바이더 골격이다.

    현재 generate 는 안전한 스텁 응답을 유지하지만,
    인증 시작에 필요한 설정값과 authorization URL 형태는 실제 구조에 가깝게 먼저 노출한다.
    """

    name = "openai_oauth"
    auth_type = "oauth"
    required_env_names = [
        "HEYGENT_OPENAI_OAUTH_CLIENT_ID",
        "HEYGENT_OPENAI_OAUTH_CLIENT_SECRET",
        "HEYGENT_OPENAI_OAUTH_REDIRECT_URI",
        "HEYGENT_OPENAI_OAUTH_AUTHORIZE_URL",
        "HEYGENT_OPENAI_OAUTH_TOKEN_URL",
    ]

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def missing_env(self) -> list[str]:
        missing: list[str] = []
        if not self.settings.openai_oauth_client_id:
            missing.append("HEYGENT_OPENAI_OAUTH_CLIENT_ID")
        if not self.settings.openai_oauth_client_secret:
            missing.append("HEYGENT_OPENAI_OAUTH_CLIENT_SECRET")
        if not self.settings.openai_oauth_redirect_uri:
            missing.append("HEYGENT_OPENAI_OAUTH_REDIRECT_URI")
        if not self.settings.openai_oauth_authorize_url:
            missing.append("HEYGENT_OPENAI_OAUTH_AUTHORIZE_URL")
        if not self.settings.openai_oauth_token_url:
            missing.append("HEYGENT_OPENAI_OAUTH_TOKEN_URL")
        return missing

    def health(self) -> ProviderHealthResponse:
        missing_env = self.missing_env()
        configured = not missing_env
        detail = "oauth 설정 준비 완료" if configured else "oauth 설정이 아직 부족해 스텁 모드로 동작합니다"
        return ProviderHealthResponse(
            provider_name=self.name,
            healthy=True,
            configured=configured,
            auth_type=self.auth_type,
            detail=detail,
            missing_env=missing_env,
        )

    def start_auth(self, *, redirect_uri: str | None = None, state: str | None = None) -> ProviderAuthResponse:
        """실제 토큰 교환 이전 단계인 authorization URL 구성을 반환한다."""

        missing_env = self.missing_env()
        effective_redirect_uri = redirect_uri or self.settings.openai_oauth_redirect_uri
        effective_state = state or new_id("oauth_state")

        if missing_env:
            return ProviderAuthResponse(
                provider_name=self.name,
                status="configuration_required",
                detail="OAuth 시작 전에 필요한 환경 변수를 먼저 채워야 합니다",
                redirect_uri=effective_redirect_uri,
                scopes=self.settings.openai_oauth_scopes,
                state=effective_state,
                missing_env=missing_env,
                metadata={"token_exchange_ready": False},
            )

        query = urlencode(
            {
                "response_type": "code",
                "client_id": self.settings.openai_oauth_client_id,
                "redirect_uri": effective_redirect_uri,
                "scope": " ".join(self.settings.openai_oauth_scopes),
                "state": effective_state,
            }
        )
        authorization_url = f"{self.settings.openai_oauth_authorize_url}?{query}"
        return ProviderAuthResponse(
            provider_name=self.name,
            status="authorization_required",
            detail="브라우저에서 authorization_url 을 열어 OpenAI OAuth 인가를 진행할 수 있습니다",
            authorization_url=authorization_url,
            redirect_uri=effective_redirect_uri,
            scopes=self.settings.openai_oauth_scopes,
            state=effective_state,
            metadata={"token_exchange_ready": True, "token_url": self.settings.openai_oauth_token_url},
        )

    def generate(self, prompt: str, **kwargs) -> ProviderGenerateResponse:
        preview = prompt.strip()[:120]
        health = self.health()
        return ProviderGenerateResponse(
            provider_name=self.name,
            output_text=f"[stub:{self.name}] {preview}",
            usage={"prompt_tokens": max(1, len(preview.split()))},
            metadata={
                "mode": "stub",
                "auth_type": self.auth_type,
                "configured": health.configured,
                "missing_env": health.missing_env,
                **kwargs,
            },
        )
