from __future__ import annotations

from app.contracts.provider.provider_response import ProviderHealthResponse
from app.domain.providers.base import BaseProvider


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
