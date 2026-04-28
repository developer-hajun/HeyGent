from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from app.domain.providers.registry import ProviderRegistry


@dataclass(slots=True)
class ProviderContext:
    """Provider 조회용 의존성을 한 번에 넘기기 위한 컨텍스트다."""

    registry: ProviderRegistry


def get_provider_context(request: Request) -> ProviderContext:
    return ProviderContext(registry=request.app.state.provider_registry)
