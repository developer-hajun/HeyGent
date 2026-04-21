from __future__ import annotations

from abc import ABC, abstractmethod

from app.contracts.provider.provider_response import ProviderAuthResponse, ProviderGenerateResponse, ProviderHealthResponse


class BaseProvider(ABC):
    """모델 SDK 직접 의존을 숨기는 최소 Provider 인터페이스다."""

    name: str

    @abstractmethod
    def health(self) -> ProviderHealthResponse:
        """현재 프로바이더 사용 가능 여부를 반환한다."""

    @abstractmethod
    def start_auth(self, *, redirect_uri: str | None = None, state: str | None = None) -> ProviderAuthResponse:
        """OAuth 시작에 필요한 메타데이터를 반환한다.

        현재 단계에서는 실제 callback 처리를 완성하지 않더라도,
        어떤 설정이 필요하고 어떤 authorization URL 로 이동해야 하는지는
        공통 인터페이스로 노출해 두는 것이 중요하다.
        """

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> ProviderGenerateResponse:
        """텍스트 생성 요청을 수행한다."""
