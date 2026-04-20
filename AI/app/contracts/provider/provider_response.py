from __future__ import annotations

from typing import Any

from pydantic import Field

from app.contracts.common.base import ContractModel


class ProviderHealthResponse(ContractModel):
    """Provider 상태 확인 응답이다."""

    provider_name: str
    healthy: bool
    detail: str


class ProviderGenerateResponse(ContractModel):
    """Provider 생성 응답 스키마다."""

    provider_name: str
    output_text: str
    usage: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
