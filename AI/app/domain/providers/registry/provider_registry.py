from __future__ import annotations

from app.contracts.provider.provider_response import ProviderHealthResponse
from app.domain.providers.model.base import BaseProvider


class ProviderRegistry:
    """Provider 등록과 조회를 담당하는 얇은 레지스트리다."""

    def __init__(self, providers: list[BaseProvider] | None = None) -> None:
        self._providers: dict[str, BaseProvider] = {}
        for provider in providers or []:
            self.register(provider)

    def register(self, provider: BaseProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, provider_name: str) -> BaseProvider:
        try:
            return self._providers[provider_name]
        except KeyError as error:
            raise KeyError(provider_name) from error

    def list_names(self) -> list[str]:
        return sorted(self._providers)

    def health(self) -> list[ProviderHealthResponse]:
        return [self._providers[name].health() for name in self.list_names()]

    def preferred_model_provider(self) -> BaseProvider:
        """기본 capability 가 사용할 모델 provider 를 고른다.

        우선순위는 API key 기반 OpenAI, 그다음 OAuth 기반 OpenAI 다.
        둘 다 없으면 등록 순서의 첫 provider 를 사용한다.
        """

        for provider_name in ("openai_api", "openai_oauth"):
            provider = self._providers.get(provider_name)
            if provider is None:
                continue
            health = provider.health()
            if health.connected or health.configured:
                return provider

        try:
            return self._providers[self.list_names()[0]]
        except IndexError as error:
            raise KeyError("no provider registered") from error
