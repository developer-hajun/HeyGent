from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, BaseModel, Field


class CreateTaskRequest(BaseModel):
    intent_type: str = Field(default="agent.loop", description="사용자 요청을 처리할 agent loop 진입 타입")
    entry_executor_key: str | None = Field(default=None, description="이전 executor 직접 지정 필드는 더 이상 사용하지 않음")
    input_payload: dict[str, Any] = Field(default_factory=dict)
    owner_key: str = "local-user"
    session_key: str | None = Field(default=None, validation_alias=AliasChoices("session_key", "sessionKey"))


class ResumeTaskRequest(BaseModel):
    approval_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
