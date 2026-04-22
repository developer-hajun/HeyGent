from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.domain.tasks.step_detail import build_default_step_detail


@dataclass(slots=True)
class TaskRun:
    """TaskRun 상태 전체를 담는 최소 도메인 모델이다."""

    # TaskRun 자체를 식별하는 고유 ID. step/event/approval 이 모두 이 값을 기준으로 묶인다.
    task_run_id: str
    # 사용자가 어떤 종류의 작업을 요청했는지 나타내는 내부 타입명.
    # 목록/필터링/라우팅에서 "이 작업이 무슨 일인지" 구분할 때 필요하다.
    task_type: str
    # 실제 실행에 사용된 flow 이름. 같은 task_type 이더라도 어떤 실행 흐름을 탔는지 추적하려고 저장한다.
    flow_name: str
    # 작업 소유자 또는 실행 주체를 구분하는 키.
    # 나중에 멀티 유저/멀티 세션으로 가더라도 작업 범위를 나누는 기준이 된다.
    owner_key: str
    # 현재 작업 상태(PENDING/RUNNING/WAITING/COMPLETED 등).
    # UI, 재개 처리, 후속 로직이 모두 이 상태를 보고 분기한다.
    status: str
    # 사람이 읽기 쉬운 작업 제목.
    # task_type 만으로는 화면에서 의미가 약해서 목록/상세 화면용 라벨로 둔다.
    title: str | None = None
    # 작업 시작에 필요한 원본 입력값.
    # "무슨 요청으로 이 TaskRun 이 만들어졌는지" 복기하려고 저장한다.
    input_payload: dict[str, Any] = field(default_factory=dict)
    # 작업이 끝난 뒤 최종 결과를 담는 payload.
    # API 응답, 후속 처리, 디버깅에서 최종 산출물을 재사용할 수 있게 한다.
    result_payload: dict[str, Any] = field(default_factory=dict)
    # 사용자 승인 등으로 멈춘 이유와 재개에 필요한 문맥.
    # WAITING 상태를 단순 상태값이 아니라 "왜 멈췄는지"까지 설명해 주는 저장소다.
    wait_payload: dict[str, Any] = field(default_factory=dict)
    # 실패했을 때 사용자/개발자가 바로 볼 수 있는 핵심 에러 문장.
    # result_payload 와 분리해서 상태 확인 화면에서 빠르게 노출하기 좋게 둔다.
    error_message: str | None = None
    # 진행 상황을 한 줄로 요약한 텍스트.
    # 긴 payload 를 열지 않아도 현재 어디까지 왔는지 보여 주려고 저장한다.
    progress_summary: str | None = None
    # 낙관적 갱신이나 변경 추적용 버전 값.
    # 여러 번 상태가 바뀌는 TaskRun 이 최신인지 판단하는 기준으로 쓸 수 있다.
    revision: int = 0
    created_at: datetime | None = None
    started_at: datetime | None = None
    updated_at: datetime | None = None
    ended_at: datetime | None = None


@dataclass(slots=True)
class StepRun:
    """StepRun 은 TaskRun 내부 단계 단위 실행 상태를 나타낸다."""

    # 개별 step 실행을 식별하는 고유 ID.
    # 이벤트, 승인 요청, 상세 조회가 특정 step 을 가리킬 때 사용한다.
    step_run_id: str
    # 어느 TaskRun 에 속한 step 인지 나타내는 부모 참조값.
    # step 단독으로 저장돼도 원래 작업과 다시 연결할 수 있어야 한다.
    task_run_id: str
    # TaskRun 안에서 몇 번째 단계인지 나타내는 순서.
    # step 목록을 원래 실행 순서대로 복원하려고 필요하다.
    step_order: int
    # 단계의 내부 타입명.
    # 예: approval.wait, model.generate 같은 실행 의미를 코드와 UI가 같이 이해할 수 있게 한다.
    step_type: str
    # 현재 step 상태.
    # TaskRun 전체 상태와 별개로 "어느 단계가 멈췄는지/실패했는지" 파악하려고 저장한다.
    status: str
    # 사람이 읽는 단계 제목.
    # 내부 타입명만 노출하면 이해가 어려워서 UI 표시용 이름을 따로 둔다.
    title: str | None = None
    # 이 step 에 들어간 입력값.
    # 이전 단계 결과를 어떤 형태로 받아 실행했는지 확인할 수 있어야 한다.
    input_payload: dict[str, Any] = field(default_factory=dict)
    # 이 step 이 만들어 낸 출력값.
    # Task 전체 결과와 별개로 단계별 산출물을 추적해야 디버깅과 재사용이 쉬워진다.
    output_payload: dict[str, Any] = field(default_factory=dict)
    # step 단위 대기 정보.
    # TaskRun.wait_payload 가 전체 작업 문맥이라면, 이 값은 정확히 어느 단계에서 왜 멈췄는지 기록한다.
    wait_payload: dict[str, Any] = field(default_factory=dict)
    # step 실행 중 내부적으로 사용한 agent/tool/llm 정보를 모아 둔 확장 필드.
    # 별도 테이블을 아직 나누지 않은 상태에서 실행 상세를 남기기 위한 핵심 스키마다.
    detail_json: dict[str, Any] = field(default_factory=build_default_step_detail)
    # 화면에 바로 보여 줄 수 있는 step 요약 문장.
    # output_payload 전체를 보지 않아도 현재 단계 결과를 빠르게 이해하게 해 준다.
    summary_message: str | None = None
    # step 실패 원인 요약.
    # Task 전체 실패와 별개로 어느 단계에서 깨졌는지 바로 찾게 해 준다.
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
