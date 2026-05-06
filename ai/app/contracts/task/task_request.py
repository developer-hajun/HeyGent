from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CreateTaskRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "sessionId": "session_routine_test_001",
                "input_payload": {
                    "routineId": "routine_morning_brief",
                    "prompt": (
                        "이 세션에 설정된 아침 브리핑 루틴을 지금 즉시 실행해줘. "
                        "최근 일정, 할 일, 필요한 확인 사항을 정리해서 보고해줘."
                    ),
                },
            },
        },
    )

    input_payload: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "TaskRun에 넘길 실행 입력입니다. 보통 `prompt`에 실행 지시문을 넣고, "
            "루틴 즉시 실행이면 `routineId` 같은 루틴 식별자나 예약/외부 트리거 메타데이터를 함께 넣을 수 있습니다."
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
            "루틴 즉시 실행에서는 어떤 세션에 붙은 루틴을 실행하는지 가리키는 부모 세션 ID로 사용합니다. "
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
