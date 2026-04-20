from __future__ import annotations

from app.contracts.provider.provider_response import ProviderGenerateResponse, ProviderHealthResponse
from app.core.config import Settings
from app.domain.providers.base import BaseProvider


class OpenAIOAuthProvider(BaseProvider):
    """실호출 대신 안전한 스텁 응답을 주는 GPT 계열 프로바이더 골격이다."""

    name = "openai_oauth"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def health(self) -> ProviderHealthResponse:
        configured = bool(self.settings.openai_oauth_client_id)
        detail = "oauth 설정 감지" if configured else "oauth 미설정, 스텁 모드"
        return ProviderHealthResponse(provider_name=self.name, healthy=True, detail=detail)

    def generate(self, prompt: str, **kwargs) -> ProviderGenerateResponse:
        preview = prompt.strip()[:120]
        return ProviderGenerateResponse(
            provider_name=self.name,
            output_text=f"[stub:{self.name}] {preview}",
            usage={"prompt_tokens": max(1, len(preview.split()))},
            metadata={"mode": "stub", **kwargs},
        )
