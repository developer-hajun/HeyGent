from __future__ import annotations

from abc import ABC, abstractmethod

from app.contracts.provider.provider_response import ProviderGenerateResponse, ProviderHealthResponse


class BaseProvider(ABC):
    """모델 SDK 직접 의존을 숨기는 최소 Provider 인터페이스다."""

    name: str

    @abstractmethod
    def health(self) -> ProviderHealthResponse:
        """현재 프로바이더 사용 가능 여부를 반환한다."""

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> ProviderGenerateResponse:
        """텍스트 생성 요청을 수행한다."""
