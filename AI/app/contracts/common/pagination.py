from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import Field

from app.contracts.common.base import ContractModel

T = TypeVar("T")


class PageInfo(ContractModel):
    """목록 응답의 최소 메타데이터다."""

    total: int = 0
    limit: int = 50
    offset: int = 0


class PaginatedResponse(ContractModel, Generic[T]):
    """프로토타입 단계에서 재사용할 단순 페이지 응답이다."""

    items: list[T] = Field(default_factory=list)
    page: PageInfo = Field(default_factory=PageInfo)
