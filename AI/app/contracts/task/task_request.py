from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CreateTaskRequest(BaseModel):
    flow_name: str = Field(..., description="실행할 flow 이름")
    input_payload: dict[str, Any] = Field(default_factory=dict)
    owner_key: str = "local-user"


class ResumeTaskRequest(BaseModel):
    approval_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
