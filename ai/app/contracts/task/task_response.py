from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus


class ApprovalStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELED = "CANCELED"


AgentKind = Literal["main", "user_subagent", "worker", "domain"]
TaskRunSource = Literal["active", "recent"]


class AgentRefResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str | None = Field(default=None, description="에이전트를 구분하는 안정적인 ID입니다.")
    kind: AgentKind | None = Field(
        default=None,
        description="에이전트 종류입니다. 기본값은 `main`, `user_subagent`, `worker`, `domain` 중 하나입니다.",
    )
    display_name: str | None = Field(default=None, alias="displayName", description="화면에 표시할 에이전트 이름입니다.")
    profile_id: str | None = Field(default=None, alias="profileId", description="사용자/기본 제공 에이전트 프로필 ID입니다.")
    profile_key: str | None = Field(
        default=None,
        alias="profileKey",
        description="프론트가 자체 시각 설정을 매핑할 때 참고할 수 있는 프로필 키입니다. 서버는 스프라이트, 좌표, 크기 같은 시각 설정을 제공하지 않습니다.",
    )
    agent_session_id: str | None = Field(default=None, alias="agentSessionId", description="이 에이전트의 실행 대화/세션 ID입니다.")
    status: str | None = Field(default=None, description="에이전트 실행 상태입니다. 있으면 TaskRun/StepRun 상태값과 같은 대문자 상태를 사용합니다.")
    summary: str | None = Field(default=None, description="에이전트가 수행 중이거나 완료한 일의 짧은 요약입니다.")
    work_id: str | None = Field(default=None, alias="workId", description="이 에이전트가 연결된 작업 ID입니다.")
    identifier: str | None = Field(default=None, description="프로필이 없을 때 구분에 사용할 보조 식별자입니다.")


class TaskRunDisplayContextResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    session_id: str | None = Field(default=None, alias="sessionId", description="TaskRun이 속한 AI 세션 ID입니다.")
    task_run_id: str | None = Field(default=None, alias="taskRunId", description="표시 컨텍스트가 가리키는 TaskRun ID입니다.")
    step_run_id: str | None = Field(default=None, alias="stepRunId", description="StepRun 단위 컨텍스트이면 StepRun ID가 들어갑니다.")
    assignee_agent: AgentRefResponse | None = Field(default=None, alias="assigneeAgent", description="TaskRun을 담당하는 에이전트입니다.")
    actor_agent: AgentRefResponse | None = Field(default=None, alias="actorAgent", description="현재 StepRun 또는 event를 실제 수행한 에이전트입니다.")
    delegated_agents: list[AgentRefResponse] = Field(default_factory=list, alias="delegatedAgents", description="현재 단계에서 같이 표시할 위임 에이전트 목록입니다.")


class PendingApprovalResponse(BaseModel):
    approval_id: str = Field(description="approval ID(승인 요청 ID)입니다. 작업을 계속하려면 `/resume`의 `approval_id`로 다시 보냅니다.")
    step_run_id: str | None = Field(default=None, description="승인을 기다리는 StepRun(작업 안의 세부 단계) ID입니다.")
    status: ApprovalStatus = Field(description="승인 요청 상태입니다. `PENDING`, `APPROVED`, `REJECTED`, `CANCELED` 중 하나입니다.")
    reason: str | None = Field(default=None, description="왜 승인이 필요한지 화면에 보여 줄 수 있는 짧은 이유입니다.")
    tool_call_id: str | None = Field(default=None, description="승인 대상 tool call(모델이 호출하려는 도구 실행) ID입니다.")
    tool_name: str | None = Field(default=None, description="승인 대상 도구 이름입니다. 예: 파일 편집, 외부 API 호출 등입니다.")
    requested_at: str | None = Field(default=None, description="승인 요청이 생성된 시각입니다.")
    can_approve: bool = Field(default=False, description="현재 사용자가 승인할 수 있으면 `true`입니다.")
    can_reject: bool = Field(default=False, description="현재 사용자가 거절할 수 있으면 `true`입니다.")


class StepRunResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    step_run_id: str = Field(description="StepRun ID(작업 안의 세부 단계 ID)입니다.")
    task_run_id: str = Field(description="이 StepRun이 속한 TaskRun(사용자 요청 하나의 실행 묶음) ID입니다.")
    step_order: int = Field(description="TaskRun 안에서 몇 번째 단계인지 나타내는 순서입니다. 작은 숫자가 먼저 실행됩니다.")
    step_type: str = Field(description="단계 종류입니다. 예: `agent.loop.execute`는 AI 루프 실행 단계입니다.")
    status: StepStatus = Field(description="단계 상태입니다. `PENDING`, `RUNNING`, `WAITING`, `BLOCKED`, `COMPLETED`, `FAILED`, `CANCELED` 중 하나입니다.")
    title: str | None = Field(default=None, description="화면에 보여 줄 단계 제목입니다.")
    semantic: TaskRunFlowSemanticResponse | None = Field(default=None, description="semantic step(계획상 의미 있는 작업 단계) 설명입니다.")
    is_current: bool = Field(default=False, description="현재 실행 중이거나 화면에서 강조해야 하는 단계이면 `true`입니다.")
    is_projected: bool = Field(default=False, description="projection(빠른 화면 조회용 Redis 복사본)이나 계획에서 미리 만들어진 단계이면 `true`입니다.")
    worker_session_id: str | None = Field(default=None, description="이 단계가 subagent/worker(하위 AI 실행자)를 만들었을 때 연결되는 AgentSession ID입니다.")
    worker_session: TaskRunFlowWorkerSessionResponse | None = Field(default=None, description="연결된 worker AgentSession(하위 AI 대화/도구 기록 세션)의 요약입니다.")
    input_payload: dict[str, Any] = Field(default_factory=dict, description="이 단계가 실행될 때 사용한 입력 데이터입니다. 디버깅과 상세 화면용입니다.")
    output_payload: dict[str, Any] = Field(default_factory=dict, description="이 단계가 만든 출력 데이터입니다. 결과 상세나 디버깅에 사용합니다.")
    wait_payload: dict[str, Any] = Field(default_factory=dict, description="단계가 `WAITING`일 때 기다리는 이유와 추가 입력 요구사항을 담습니다.")
    pending_approval: PendingApprovalResponse | None = Field(default=None, alias="pendingApproval", description="사용자 승인이 필요한 상태이면 승인 정보가 들어갑니다.")
    display_context: TaskRunDisplayContextResponse = Field(default_factory=TaskRunDisplayContextResponse, alias="displayContext", description="시각화 화면에서 StepRun을 담당/실행 에이전트에 매핑하는 표시 컨텍스트입니다.")
    # approval 은 UI가 wait/detail payload를 직접 해석하지 않도록 별도 view로도 노출한다.
    detail_json: dict[str, Any] = Field(default_factory=dict, description="내부 실행 상세 정보입니다. UI가 직접 해석하기보다 디버깅/상세 보기용으로 사용합니다.")
    summary_message: str | None = Field(default=None, description="단계 진행 상황을 사람이 읽기 쉽게 요약한 문장입니다.")
    error_message: str | None = Field(default=None, description="단계 실패 이유입니다. 실패가 아니면 `null`입니다.")
    created_at: datetime | None = Field(default=None, description="단계 레코드가 생성된 시각입니다.")
    updated_at: datetime | None = Field(default=None, description="단계 레코드가 마지막으로 갱신된 시각입니다.")
    started_at: datetime | None = Field(default=None, description="단계 실행이 시작된 시각입니다.")
    ended_at: datetime | None = Field(default=None, description="단계 실행이 끝난 시각입니다.")


class TaskRunResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    task_run_id: str = Field(description="TaskRun ID(사용자 요청 하나의 실행 묶음 ID)입니다. 상세/flow/events/resume/cancel 호출에 사용합니다.")
    task_type: str = Field(description="실제로 실행된 TaskRun 종류입니다. 보통 `agent.loop`입니다.")
    session_key: str | None = Field(default=None, description="sessionId의 내부 저장명입니다. 같은 AI 세션의 실행을 묶는 값입니다.")
    current_step_run_id: str | None = Field(default=None, description="현재 실행 중이거나 마지막으로 진행된 StepRun ID입니다.")
    status: TaskStatus = Field(description="TaskRun 상태입니다. `PENDING`, `RUNNING`, `WAITING`, `BLOCKED`, `COMPLETED`, `FAILED`, `CANCELED` 중 하나입니다.")
    title: str | None = Field(default=None, description="목록이나 상세 상단에 보여 줄 작업 제목입니다.")
    input_payload: dict[str, Any] = Field(default_factory=dict, description="생성 요청에서 받은 사용자 입력입니다.")
    result_payload: dict[str, Any] = Field(default_factory=dict, description="TaskRun이 완료되며 만든 최종 결과 데이터입니다.")
    todo_state: dict[str, Any] = Field(default_factory=dict, description="Task Engine(작업 실행 엔진)이 내부 계획/할 일 상태를 저장하는 객체입니다. 보통 디버깅용입니다.")
    wait_payload: dict[str, Any] = Field(default_factory=dict, description="TaskRun이 `WAITING`일 때 사용자가 무엇을 해야 하는지 담는 객체입니다.")
    pending_approval: PendingApprovalResponse | None = Field(default=None, alias="pendingApproval", description="사용자 승인 대기 상태이면 승인 요청 정보가 들어갑니다.")
    display_context: TaskRunDisplayContextResponse = Field(default_factory=TaskRunDisplayContextResponse, alias="displayContext", description="시각화 화면에서 TaskRun을 담당 에이전트에 매핑하는 표시 컨텍스트입니다.")
    error_message: str | None = Field(default=None, description="TaskRun 실패 이유입니다. 실패가 아니면 `null`입니다.")
    progress_summary: str | None = Field(default=None, description="현재까지 진행 상황을 사람이 읽기 쉽게 요약한 문장입니다.")
    revision: int = Field(description="TaskRun 수정 번호입니다. 값이 커지면 상태나 결과가 갱신된 것입니다.")
    created_at: datetime | None = Field(default=None, description="TaskRun이 생성된 시각입니다.")
    started_at: datetime | None = Field(default=None, description="TaskRun 실행이 시작된 시각입니다.")
    updated_at: datetime | None = Field(default=None, description="TaskRun이 마지막으로 갱신된 시각입니다.")
    ended_at: datetime | None = Field(default=None, description="TaskRun이 완료/실패/취소로 끝난 시각입니다.")


class StepRunSummaryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    step_run_id: str = Field(description="StepRun ID(작업 안의 세부 단계 ID)입니다.")
    step_order: int = Field(description="TaskRun 안에서의 단계 순서입니다.")
    step_type: str = Field(description="단계 종류입니다.")
    status: StepStatus = Field(description="단계 상태입니다.")
    title: str | None = Field(default=None, description="단계 제목입니다.")
    summary_message: str | None = Field(default=None, description="단계 진행 요약입니다.")
    updated_at: datetime | None = Field(default=None, description="단계가 마지막으로 갱신된 시각입니다.")
    display_context: TaskRunDisplayContextResponse = Field(default_factory=TaskRunDisplayContextResponse, alias="displayContext", description="시각화 화면에서 StepRun 요약을 실행 에이전트에 매핑하는 표시 컨텍스트입니다.")


class TaskRunListItemResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    task_run_id: str = Field(description="TaskRun ID(사용자 요청 하나의 실행 묶음 ID)입니다.")
    task_type: str = Field(description="실제로 실행된 TaskRun 종류입니다.")
    session_key: str | None = Field(default=None, description="sessionId의 내부 저장명입니다.")
    status: TaskStatus = Field(description="TaskRun 상태입니다.")
    title: str | None = Field(default=None, description="목록에 표시할 작업 제목입니다.")
    input_summary: str | None = Field(default=None, description="사용자 입력을 한 줄로 줄인 요약입니다.")
    step_count: int = Field(default=0, description="이 TaskRun에 포함된 StepRun 개수입니다.")
    progress_summary: str | None = Field(default=None, description="진행 상황 요약입니다.")
    created_at: datetime | None = Field(default=None, description="TaskRun 생성 시각입니다.")
    updated_at: datetime | None = Field(default=None, description="TaskRun 마지막 갱신 시각입니다.")
    current_step: StepRunSummaryResponse | None = Field(default=None, description="현재 또는 마지막 대표 StepRun 요약입니다.")
    display_context: TaskRunDisplayContextResponse = Field(default_factory=TaskRunDisplayContextResponse, alias="displayContext", description="시각화 화면에서 목록 항목을 담당 에이전트에 매핑하는 표시 컨텍스트입니다.")


class TaskRunListResponse(BaseModel):
    items: list[TaskRunListItemResponse] = Field(default_factory=list, description="현재 페이지의 TaskRun 목록입니다.")
    page: int = Field(description="현재 페이지 번호입니다. 1부터 시작합니다.")
    page_size: int = Field(description="한 페이지에 담긴 최대 항목 수입니다.")
    total_count: int = Field(description="조건에 맞는 전체 TaskRun 개수입니다.")
    has_previous: bool = Field(description="이전 페이지가 있으면 `true`입니다.")
    has_next: bool = Field(description="다음 페이지가 있으면 `true`입니다.")
    status_filter: str = Field(description="적용된 상태 필터입니다. 필터가 없으면 `ALL`입니다.")


class TaskRunFlowSemanticResponse(BaseModel):
    key: str | None = Field(default=None, description="semantic step(계획상 의미 있는 단계)을 구분하는 내부 키입니다.")
    step: str | None = Field(default=None, description="사람이 읽을 수 있는 계획 단계 이름입니다.")
    goal: str | None = Field(default=None, description="이 단계가 달성하려는 목표입니다.")
    status: str | None = Field(default=None, description="계획 단계 기준 상태입니다.")


class TaskRunFlowActivityResponse(BaseModel):
    event_type: str = Field(description="event(시간순 진행 기록) 종류입니다. 예: `task.created`, `step.completed`.")
    status: TaskStatus | StepStatus | None = Field(default=None, description="이 event 발생 시점의 TaskRun 또는 StepRun 상태입니다.")
    summary_message: str | None = Field(default=None, description="이 event를 사람이 읽기 쉽게 요약한 문장입니다.")
    occurred_at: str = Field(description="event가 발생한 시각입니다.")


class TaskRunFlowWorkerSessionResponse(BaseModel):
    session_id: str = Field(description="AgentSession ID(하위 AI 대화/도구 기록 세션 ID)입니다.")
    status: str | None = Field(default=None, description="worker/subagent(하위 AI 실행자) 세션 상태입니다.")
    summary: str | None = Field(default=None, description="worker가 수행한 작업 요약입니다.")
    agent_id: str | None = Field(default=None, description="worker 실행자를 구분하는 ID입니다.")
    profile_key: str | None = Field(default=None, description="worker가 사용한 프로필 키입니다.")


class TaskRunFlowNodeResponse(BaseModel):
    step_run_id: str = Field(description="그래프 노드가 나타내는 StepRun ID입니다.")
    step_order: int = Field(description="TaskRun 안의 단계 순서입니다.")
    title: str | None = Field(default=None, description="그래프에 표시할 단계 제목입니다.")
    status: StepStatus = Field(description="노드의 현재 상태입니다.")
    step_type: str = Field(description="노드가 나타내는 단계 종류입니다.")
    semantic: TaskRunFlowSemanticResponse | None = Field(default=None, description="이 노드에 연결된 계획 단계 설명입니다.")
    is_current: bool = Field(description="현재 진행 중인 노드이면 `true`입니다.")
    is_projected: bool = Field(description="실행 전 계획/projection에서 만들어진 노드이면 `true`입니다.")
    worker_session_id: str | None = Field(default=None, description="이 노드가 만든 worker AgentSession ID입니다.")
    worker_session: TaskRunFlowWorkerSessionResponse | None = Field(default=None, description="worker AgentSession 요약입니다.")
    activity: list[TaskRunFlowActivityResponse] = Field(default_factory=list, description="이 노드에서 발생한 event 요약 목록입니다.")


class TaskRunFlowEdgeResponse(BaseModel):
    from_step_run_id: str | None = Field(default=None, description="연결 시작 StepRun ID입니다.")
    to_step_run_id: str | None = Field(default=None, description="다음 StepRun으로 이어질 때의 도착 StepRun ID입니다.")
    to_task_run_id: str | None = Field(default=None, description="다른 TaskRun으로 이어질 때의 도착 TaskRun ID입니다. 현재는 확장용입니다.")
    to_agent_session_id: str | None = Field(default=None, description="worker/subagent로 위임될 때 메시지를 조회할 AgentSession ID입니다.")
    relation: str = Field(description="연결 의미입니다. `next`는 다음 단계, `delegates_to`는 worker/subagent 위임입니다.")


class TaskRunFlowResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    task_run_id: str = Field(description="flow(진행 그래프)를 조회한 TaskRun ID입니다.")
    status: TaskStatus = Field(description="TaskRun 현재 상태입니다.")
    title: str | None = Field(default=None, description="flow 화면 상단에 표시할 제목입니다.")
    current_step_run_id: str | None = Field(default=None, description="현재 강조할 StepRun ID입니다.")
    summary: str | None = Field(default=None, description="TaskRun 전체 진행 요약입니다.")
    pending_approval: PendingApprovalResponse | None = Field(default=None, alias="pendingApproval", description="flow 전체에서 현재 열린 승인 요청입니다.")
    nodes: list[TaskRunFlowNodeResponse] = Field(default_factory=list, description="flow 그래프의 노드 목록입니다. 보통 StepRun 하나가 노드 하나입니다.")
    edges: list[TaskRunFlowEdgeResponse] = Field(default_factory=list, description="flow 그래프의 연결 목록입니다. 단계 순서와 subagent 위임 관계를 보여 줍니다.")


class ActiveTaskRunCurrentStepResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    step_run_id: str = Field(description="현재 StepRun ID입니다.")
    title: str | None = Field(default=None, description="현재 단계 제목입니다.")
    status: StepStatus = Field(description="현재 단계 상태입니다.")
    display_context: TaskRunDisplayContextResponse = Field(default_factory=TaskRunDisplayContextResponse, alias="displayContext", description="시각화 화면에서 현재 StepRun을 실행 에이전트에 매핑하는 표시 컨텍스트입니다.")


class ActiveTaskRunListItemResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    task_run_id: str = Field(description="활성 또는 최근 TaskRun ID입니다.")
    source: TaskRunSource = Field(description="목록에 들어온 이유입니다. `active`는 실행/대기 중, `recent`는 방금 끝난 작업입니다.")
    session_key: str | None = Field(default=None, description="sessionId의 내부 저장명입니다.")
    status: TaskStatus = Field(description="TaskRun 상태입니다.")
    title: str | None = Field(default=None, description="화면에 표시할 작업 제목입니다.")
    current_step_run_id: str | None = Field(default=None, description="현재 또는 마지막 대표 StepRun ID입니다.")
    current_step: ActiveTaskRunCurrentStepResponse | None = Field(default=None, description="현재 또는 마지막 대표 StepRun 요약입니다.")
    updated_at: datetime | None = Field(default=None, description="TaskRun 마지막 갱신 시각입니다.")
    wait_reason: str | None = Field(default=None, description="작업이 기다리는 이유입니다. 현재 승인 대기는 `approval_required`를 사용합니다.")
    pending_approval: PendingApprovalResponse | None = Field(default=None, alias="pendingApproval", description="승인 대기 중이면 승인 정보가 들어갑니다.")
    display_context: TaskRunDisplayContextResponse = Field(default_factory=TaskRunDisplayContextResponse, alias="displayContext", description="시각화 화면에서 활성 TaskRun을 담당 에이전트에 매핑하는 표시 컨텍스트입니다.")


class ActiveTaskRunListResponse(BaseModel):
    items: list[ActiveTaskRunListItemResponse] = Field(default_factory=list, description="활성 작업과 최근 종료 작업 목록입니다.")
    total_count: int = Field(description="반환된 항목 개수입니다.")


class TaskEventResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event_id: str = Field(description="event ID(시간순 진행 기록 ID)입니다.")
    event_id_alias: str | None = Field(default=None, alias="eventId", description="event_id와 같은 값의 camelCase 별칭입니다. WebSocket/외부 채널에서 쓰기 쉽게 제공합니다.")
    event_type: str = Field(description="event 종류입니다. 예: `task.created`, `step.started`, `task.completed`.")
    task_run_id: str = Field(description="event가 속한 TaskRun ID입니다.")
    step_run_id: str | None = Field(default=None, description="특정 StepRun에서 발생한 event이면 StepRun ID가 들어갑니다.")
    status: TaskStatus | StepStatus | None = Field(default=None, description="event 발생 시점의 TaskRun 또는 StepRun 상태입니다.")
    summary_message: str | None = Field(default=None, description="화면 로그에 보여 줄 수 있는 진행 요약입니다.")
    payload: dict[str, Any] = Field(default_factory=dict, description="event별 추가 데이터입니다. UI가 모르는 키는 무시해도 됩니다.")
    occurred_at: str = Field(description="event가 발생한 시각입니다.")
    sequence: int | None = Field(default=None, description="TaskRun 안에서 증가하는 순번입니다. WebSocket 유실 후 `/events?afterSequence=`로 복구할 때 사용합니다.")
