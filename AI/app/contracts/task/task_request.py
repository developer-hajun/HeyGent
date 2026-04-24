from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, BaseModel, Field


class CreateTaskRequest(BaseModel):
    intent_type: str = Field(..., description="사용자 요청 의도 타입")
    entry_executor_key: str | None = Field(default=None, description="필요하면 시작 executor key 를 명시")
    input_payload: dict[str, Any] = Field(default_factory=dict)
    owner_key: str = "local-user"
    session_key: str | None = Field(default=None, validation_alias=AliasChoices("session_key", "sessionKey"))


class ResumeTaskRequest(BaseModel):
    approval_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
