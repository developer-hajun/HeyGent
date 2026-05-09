from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CreateWorkRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    client_request_id: str = Field(alias="clientRequestId", description="작업 생성과 최초 실행을 묶는 중복 방지 키입니다.")
    title: str | None = Field(default=None, description="LLM이 작성한 작업 제목입니다.")
    description: str = Field(description="LLM이 작성한 작업 설명입니다.")
    assignee_agent_id: str | None = Field(default=None, alias="assigneeAgentId", description="작업을 맡을 세션 에이전트 ID입니다.")
    raw_user_input: str = Field(alias="rawUserInput", description="사용자 입력 원문입니다. 요약/정리와 별도로 반드시 보존합니다.")
    execution_instruction: str = Field(alias="executionInstruction", description="최초 TaskRun에 넘길 실행 지시입니다.")
    start_execution: bool = Field(default=True, alias="startExecution", description="생성 직후 실행까지 시작할지 여부입니다.")
    expected_deliverable: str | None = Field(default=None, alias="expectedDeliverable", description="기대 산출물입니다.")
    acceptance_criteria: list[str] = Field(default_factory=list, alias="acceptanceCriteria", description="완료 판단을 돕는 기준입니다.")
    constraints: list[str] = Field(default_factory=list, description="마감, 형식, 범위 같은 제약입니다.")
    label_names: list[str] = Field(default_factory=list, alias="labelNames", description="기존 라벨 이름과 매칭할 후보입니다.")
    initial_comment: str | None = Field(default=None, alias="initialComment", description="생성 직후 남길 초기 댓글입니다.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="작업 생성 해석 결과입니다.")


class CreateWorkCommentRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    body: str = Field(description="댓글 본문입니다.")
    resume: bool = Field(default=False, description="완료된 작업을 명시적으로 다시 움직일지 여부입니다.")


class MoveWorkStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(description="변경할 작업 상태입니다.")


class UpdateWorkFieldsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200, description="변경할 작업 제목입니다.")
    description: str | None = Field(default=None, max_length=10_000, description="변경할 작업 설명입니다.")


class UpdateWorkAssigneeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    assignee_agent_id: str | None = Field(default=None, alias="assigneeAgentId", description="작업을 맡을 세션 에이전트 ID입니다.")


class SetWorkLabelsRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    label_ids: list[str] = Field(default_factory=list, alias="labelIds", description="연결할 라벨 ID 목록입니다.")
    label_names: list[str] = Field(default_factory=list, alias="labelNames", description="연결할 기존 라벨 이름 목록입니다.")


class CreateWorkLabelRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    name: str = Field(min_length=1, max_length=80, description="라벨 이름입니다.")
    color: str = Field(default="#64748b", max_length=32, description="라벨 색상입니다.")


class UpdateWorkLabelRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=80, description="변경할 라벨 이름입니다.")
    color: str | None = Field(default=None, max_length=32, description="변경할 라벨 색상입니다.")


class UpsertWorkRelationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    target_work_id: str = Field(alias="targetWorkId", description="관계를 연결할 대상 작업 ID입니다.")
    relation_type: str = Field(alias="relationType", description="blocks 또는 related 입니다.")


class CreateWorkRunRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    message: str = Field(default="이 작업을 이어서 진행해.", description="작업 실행 시 채팅에 남길 메시지입니다.")
    client_message_id: str | None = Field(default=None, alias="clientMessageId", description="채팅 메시지 중복 방지 키입니다.")
    include_comments: bool = Field(default=True, alias="includeComments", description="MVP에서는 항상 true로 처리합니다.")
    include_recent_runs: bool = Field(default=True, alias="includeRecentRuns", description="최근 실행 컨텍스트 포함 여부입니다.")
