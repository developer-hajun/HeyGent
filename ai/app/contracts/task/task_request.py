from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CreateTaskRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "intent_type": "agent.loop",
                "sessionId": "session_research_test_001",
                "input_payload": {
                    "prompt": (
                        "최근 AI 에이전트 오케스트레이션에서 subagent를 쓰는 이유를 간단히 조사해줘. "
                        "가능하면 worker/subagent에게 자료 조사를 맡기고, 부모 agent는 결과를 종합해서 "
                        "핵심 이유 3가지와 주의점 2가지를 한국어로 정리해줘. "
                        "웹검색을 사용할 수 없으면 그 한계를 먼저 말하고, 알고 있는 범위에서 답해줘."
                    ),
                },
            },
        },
    )

    intent_type: str = Field(
        default="agent.loop",
        description=(
            "AI가 요청을 처리하는 방식입니다. 일반 사용자 요청은 기본값 `agent.loop`을 그대로 둡니다. "
            "intent(의도)는 Orchestrator(작업 시작/재개를 맡는 내부 실행 관리자)가 어떤 실행 흐름을 고를지 판단하는 값입니다."
        ),
    )
    input_payload: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "사용자가 실제로 시킨 내용을 담는 객체입니다. 보통 `prompt`에 자연어 요청을 넣습니다. "
            "필요하면 `model`, `workspacePath`, `attachments` 같은 화면/채널별 값을 함께 넣을 수 있습니다."
        ),
    )
    owner_key: str = Field(
        default="local-user",
        description=(
            "작업 소유자 키입니다. 운영/프론트 요청에서는 Authorization 토큰의 사용자 ID가 우선 적용되어 이 값은 무시됩니다. "
            "토큰 없이 로컬 테스트할 때만 fallback(대체값)으로 사용합니다."
        ),
    )
    session_key: str | None = Field(
        default=None,
        validation_alias="sessionId",
        title="Session ID",
        description=(
            "sessionId(AI가 직접 관리하는 대화 세션 ID)입니다. "
            "같은 사용자와 같은 sessionId 안에서는 동시에 실행 중인 TaskRun(사용자 요청 하나의 실행 묶음)을 하나만 허용합니다. "
            "내부 저장명은 session_key입니다."
        ),
    )


class ResumeTaskRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"approval_id": "approval_123", "payload": {"approved": True}},
        }
    )

    approval_id: str | None = Field(
        default=None,
        description=(
            "승인해야 하는 approval ID입니다. `pendingApproval.approval_id` 값을 그대로 넣습니다. "
            "approval(승인 요청)은 도구 실행이나 위험 작업 전에 사용자의 확인을 기다리는 상태입니다."
        ),
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="승인/거절 결과나 추가 입력을 담는 객체입니다. 예: `{\"approved\": true}`",
    )
