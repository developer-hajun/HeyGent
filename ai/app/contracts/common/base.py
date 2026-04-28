from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ContractModel(BaseModel):
    """외부 계약 모델의 공통 기본 설정을 모은다."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
