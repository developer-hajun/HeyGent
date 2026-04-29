from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgentSessionMessageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    role: str
    content: str | None = None
    tool_name: str | None = Field(default=None, alias="toolName")
    tool_call_id: str | None = Field(default=None, alias="toolCallId")
    tool_calls: list[dict[str, Any]] = Field(default_factory=list, alias="toolCalls")
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime | float | str | None = None
    finish_reason: str | None = Field(default=None, alias="finishReason")


class AgentSessionMessagesResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    agent_session_id: str = Field(alias="agentSessionId")
    after_message_id: int | None = Field(default=None, alias="afterMessageId")
    limit: int
    total_count: int = Field(alias="totalCount")
    next_after_message_id: int | None = Field(default=None, alias="nextAfterMessageId")
    items: list[AgentSessionMessageResponse] = Field(default_factory=list)
