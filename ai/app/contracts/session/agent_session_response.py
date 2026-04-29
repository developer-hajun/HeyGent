from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgentSessionMessageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(description="AgentSession 안에서 증가하는 메시지 번호입니다. `afterMessageId`에 넣어 다음 메시지만 조회할 수 있습니다.")
    role: str = Field(description="메시지 역할입니다. 예: `user`, `assistant`, `tool`, `system`.")
    content: str | None = Field(default=None, description="메시지 본문입니다. 도구 호출 메시지는 비어 있을 수 있습니다.")
    tool_name: str | None = Field(default=None, alias="toolName", description="도구 실행 결과 메시지일 때의 도구 이름입니다.")
    tool_call_id: str | None = Field(default=None, alias="toolCallId", description="모델이 요청한 tool call(도구 호출) ID입니다.")
    tool_calls: list[dict[str, Any]] = Field(default_factory=list, alias="toolCalls", description="assistant가 요청한 도구 호출 목록입니다. 화면에서는 디버깅/상세 보기용입니다.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="메시지에 붙은 내부 부가 정보입니다. 모르는 키는 무시해도 됩니다.")
    timestamp: datetime | float | str | None = Field(default=None, description="메시지가 기록된 시각입니다. 저장소에 따라 datetime, epoch, 문자열일 수 있습니다.")
    finish_reason: str | None = Field(default=None, alias="finishReason", description="모델 응답 종료 이유입니다. 예: `stop`, `tool_calls`, `length`.")


class AgentSessionMessagesResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    agent_session_id: str = Field(alias="agentSessionId", description="AgentSession ID(AI와 주고받은 대화/도구 호출 기록 세션 ID)입니다.")
    after_message_id: int | None = Field(default=None, alias="afterMessageId", description="요청에서 사용한 기준 메시지 번호입니다. 이 번호보다 큰 메시지만 반환합니다.")
    limit: int = Field(description="최대 반환 메시지 수입니다.")
    total_count: int = Field(alias="totalCount", description="이번 응답에 포함된 메시지 개수입니다.")
    next_after_message_id: int | None = Field(default=None, alias="nextAfterMessageId", description="다음 증분 조회 때 `afterMessageId`로 넣을 마지막 메시지 번호입니다.")
    items: list[AgentSessionMessageResponse] = Field(default_factory=list, description="AgentSession 메시지 목록입니다.")
