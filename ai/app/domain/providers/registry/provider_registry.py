from __future__ import annotations

from app.contracts.provider.provider_response import ProviderHealthResponse
from app.domain.providers.model.base import BaseProvider


class ProviderRegistry:
    """Provider 등록과 조회를 담당하는 얇은 레지스트리다."""

    _RUNTIME_PROVIDER_ALIASES = {
        "openai": "openai_api",
        "openai_api_key": "openai_api",
        "openai_user_api_key": "openai_api",
        "openai_dev_fallback": "openai_api",
        "gemini": "gemini_api",
        "gemini_api_key": "gemini_api",
    }

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

    def model_provider_for(self, provider_name: str | None) -> BaseProvider:
        normalized = str(provider_name or "").strip()
        if not normalized:
            return self.preferred_model_provider()
        registered_name = self._RUNTIME_PROVIDER_ALIASES.get(normalized, normalized)
        provider = self._providers.get(registered_name)
        if provider is not None:
            return provider
        return self.preferred_model_provider()

    def list_names(self) -> list[str]:
        return sorted(self._providers)

    def health(self) -> list[ProviderHealthResponse]:
        return [self._providers[name].health() for name in self.list_names()]

    async def aclose(self) -> None:
        for provider in self._providers.values():
            close = getattr(provider, "aclose", None)
            if callable(close):
                await close()

    def preferred_model_provider(self) -> BaseProvider:
        """기본 handler 가 사용할 모델 provider 를 고른다.

        현재 런타임 모델 호출은 backend provider credential을 발급받는
        API key 기반 OpenAI provider를 기본으로 사용한다.
        """

        for provider_name in ("openai_api",):
            provider = self._providers.get(provider_name)
            if provider is None:
                continue
            health = provider.health()
            if health.connected or health.configured or getattr(provider, "auth_type", None) == "api_key":
                return provider

        try:
            return self._providers[self.list_names()[0]]
        except IndexError as error:
            raise KeyError("no provider registered") from error
