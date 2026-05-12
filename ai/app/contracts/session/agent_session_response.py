from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SessionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_id: str = Field(alias="sessionId", description="AI 세션 ID입니다. 메시지 전송과 조회에 사용합니다.")
    title: str | None = Field(default=None, description="세션 제목입니다.")
    owner_key: str | None = Field(default=None, alias="ownerKey", description="세션 소유자 ID입니다.")
    owner_user_id: int | None = Field(default=None, alias="ownerUserId", description="DB users(id)와 연결된 세션 소유자 ID입니다.")
    status: str | None = Field(default=None, description="세션 상태입니다. 예: ACTIVE, COMPLETED, FAILED.")
    source: str | None = Field(default=None, description="세션 종류입니다. main은 일반 사용자 대화, worker는 격리된 하위 작업 세션입니다.")
    parent_session_id: str | None = Field(default=None, alias="parentSessionId", description="worker 세션이면 부모 세션 ID가 들어갑니다.")
    message_count: int = Field(default=0, alias="messageCount", description="세션에 저장된 메시지 개수입니다.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="세션 부가 정보입니다.")
    settings: dict[str, Any] = Field(default_factory=dict, description="다음 메시지 실행에 복사할 세션별 실행 설정입니다.")
    created_at: datetime | float | str | None = Field(default=None, alias="createdAt", description="세션 생성 시각입니다.")
    updated_at: datetime | float | str | None = Field(default=None, alias="updatedAt", description="마지막 메시지나 상태 변경 시각입니다.")
    ended_at: datetime | float | str | None = Field(default=None, alias="endedAt", description="세션 종료 시각입니다. 진행 중이면 비어 있습니다.")
    archived_at: datetime | float | str | None = Field(default=None, alias="archivedAt", description="세션이 아카이브된 시각입니다.")
    deleted_at: datetime | float | str | None = Field(default=None, alias="deletedAt", description="세션 삭제 요청이 기록된 시각입니다.")
    purge_after: datetime | float | str | None = Field(default=None, alias="purgeAfter", description="보존 기간이 끝난 뒤 물리 정리 가능한 시각입니다.")


class SessionListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[SessionResponse] = Field(default_factory=list, description="AI 세션 목록입니다.")
    page: int = Field(description="현재 페이지 번호입니다. 1부터 시작합니다.")
    page_size: int = Field(alias="pageSize", description="한 페이지에 담긴 최대 세션 수입니다.")
    total_count: int = Field(alias="totalCount", description="조건에 맞는 전체 공개 세션 개수입니다.")
    has_previous: bool = Field(alias="hasPrevious", description="이전 페이지가 있으면 `true`입니다.")
    has_next: bool = Field(alias="hasNext", description="다음 페이지가 있으면 `true`입니다.")


class CreateSessionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=120, description="빈 AI 세션 제목입니다.")
    model: str | None = Field(default=None, max_length=100, description="세션 기본 모델입니다.")
    settings: dict[str, Any] = Field(default_factory=dict, description="세션별 실행 설정입니다.")
    metadata_patch: dict[str, Any] | None = Field(default=None, alias="metadataPatch", description="서버가 허용한 표시용 metadata입니다.")


class CreateSessionMessageRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "content": "최근 AI 에이전트가 worker를 분리해서 쓰는 이유를 조사해줘.",
                "model": "gpt-5.4",
            },
        },
    )

    session_id: str | None = Field(
        default=None,
        alias="sessionId",
        description=(
            "이어 쓸 AI 세션 ID입니다. 비워 두고 `/sessions/messages`로 요청하면 "
            "서버가 새 세션을 자동으로 만들고 응답의 sessionId로 돌려줍니다."
        ),
    )
    content: str = Field(min_length=1, description="사용자가 보낸 메시지 본문입니다. 이 값이 모델에 전달되는 기본 prompt가 됩니다.")
    client_message_id: str | None = Field(default=None, alias="clientMessageId", description="HTTP 재시도 중복 실행을 막기 위한 클라이언트 메시지 ID입니다.")
    model: str | None = Field(default=None, max_length=100, description="이번 메시지 처리에 사용할 모델 이름입니다. 비워 두면 서버 기본 모델을 사용합니다.")
    input_payload: dict[str, Any] = Field(default_factory=dict, alias="inputPayload", description="첨부, 실행 옵션 같은 추가 입력입니다. 서버는 content를 기본 prompt로 넣습니다.")


class UpdateSessionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=120, description="변경할 세션 제목입니다.")
    metadata_patch: dict[str, Any] | None = Field(default=None, alias="metadataPatch", description="서버가 허용한 표시용 metadata만 변경합니다.")
    client_command_id: str | None = Field(default=None, alias="clientCommandId", description="클라이언트 재시도 추적용 command ID입니다.")


class ArchiveSessionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    archived: bool = Field(default=True, description="true면 아카이브하고 false면 기본 목록으로 복원합니다.")
    client_command_id: str | None = Field(default=None, alias="clientCommandId", description="클라이언트 재시도 추적용 command ID입니다.")


class UpdateSessionSettingsRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    settings: dict[str, Any] = Field(default_factory=dict, description="model, systemPrompt, toolsets, delegationPolicy만 저장할 수 있습니다.")
    client_command_id: str | None = Field(default=None, alias="clientCommandId", description="클라이언트 재시도 추적용 command ID입니다.")


class SessionMessageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(description="세션 안에서 증가하는 메시지 번호입니다. `afterMessageId`에 넣어 다음 메시지만 조회할 수 있습니다.")
    session_id: str = Field(alias="sessionId", description="이 메시지가 속한 AI 세션 ID입니다.")
    role: str = Field(description="메시지 역할입니다. 예: `user`, `assistant`.")
    content: str | None = Field(default=None, description="메시지 본문입니다.")
    task_run_id: str | None = Field(default=None, alias="taskRunId", description="assistant 메시지를 만든 TaskRun ID입니다. 사용자 메시지에는 보통 비어 있습니다.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="메시지 부가 정보입니다. 화면에서 모르는 키는 무시해도 됩니다.")
    timestamp: datetime | float | str | None = Field(default=None, description="메시지가 저장된 시각입니다.")
    finish_reason: str | None = Field(default=None, alias="finishReason", description="모델 응답 종료 이유입니다. 예: `stop`, `tool_calls`, `length`.")


class SessionMessagesResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_id: str = Field(alias="sessionId", description="조회한 AI 세션 ID입니다.")
    after_message_id: int | None = Field(default=None, alias="afterMessageId", description="요청에서 사용한 기준 메시지 번호입니다.")
    limit: int = Field(description="최대 반환 메시지 수입니다.")
    total_count: int = Field(alias="totalCount", description="이번 응답에 포함된 메시지 개수입니다.")
    next_after_message_id: int | None = Field(default=None, alias="nextAfterMessageId", description="다음 증분 조회 때 `afterMessageId`로 넣을 마지막 메시지 번호입니다.")
    items: list[SessionMessageResponse] = Field(default_factory=list, description="AI 세션의 공개 메시지 목록입니다.")


class CreateSessionMessageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_id: str = Field(alias="sessionId", description="메시지를 보낸 AI 세션 ID입니다.")
    task_run_id: str = Field(alias="taskRunId", description="이번 메시지 처리를 위해 생성된 TaskRun ID입니다.")
    status: str = Field(description="TaskRun 상태입니다.")
    user_message: SessionMessageResponse | None = Field(default=None, alias="userMessage", description="저장된 사용자 메시지입니다.")
    assistant_message: SessionMessageResponse | None = Field(default=None, alias="assistantMessage", description="저장된 assistant 응답 메시지입니다. 대기/실패 상태에서는 비어 있을 수 있습니다.")
    task: dict[str, Any] = Field(default_factory=dict, description="TaskRun 요약입니다. 상세 진행 흐름은 `/taskRuns/{taskRunId}/flow`로 조회합니다.")


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
