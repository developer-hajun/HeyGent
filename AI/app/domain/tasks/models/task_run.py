from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class TaskRun:
    """TaskRun 상태 전체를 담는 최소 도메인 모델이다."""

    # TaskRun 자체를 식별하는 고유 ID. step/event/approval 이 모두 이 값을 기준으로 묶인다.
    task_run_id: str
    # 사용자가 어떤 종류의 작업을 요청했는지 나타내는 내부 타입명.
    # 목록/필터링/라우팅에서 "이 작업이 무슨 일인지" 구분할 때 필요하다.
    task_type: str
    # 작업 소유자 또는 실행 주체를 구분하는 키.
    # 나중에 멀티 유저/멀티 세션으로 가더라도 작업 범위를 나누는 기준이 된다.
    owner_key: str
    # 현재 작업 상태(PENDING/RUNNING/WAITING/COMPLETED 등).
    # UI, 재개 처리, 후속 로직이 모두 이 상태를 보고 분기한다.
    status: str
    # 사용자가 요청한 의도 타입.
    # flow 제거 이후에는 이 값이 "무슨 작업을 하려는가"를 설명하는 정식 기준점이 된다.
    intent_type: str | None = None
    # 호환 필드: 이 TaskRun 이 처음 어떤 executor 로 진입했는지 남기는 키.
    # 2차 migration 에서 entry_executor_key 로 이름을 분리한다.
    entry_capability: str | None = None
    # 현재 루프가 붙잡고 있는 StepRun ID.
    # waiting/resume/이벤트 발행이 "마지막 step 추측"이 아니라 정확한 step 기준으로 움직이게 만드는 최소 앵커다.
    current_step_run_id: str | None = None
    # 사람이 읽기 쉬운 작업 제목.
    # task_type 만으로는 화면에서 의미가 약해서 목록/상세 화면용 라벨로 둔다.
    title: str | None = None
    # 작업 시작에 필요한 원본 입력값.
    # "무슨 요청으로 이 TaskRun 이 만들어졌는지" 복기하려고 저장한다.
    input_payload: dict[str, Any] = field(default_factory=dict)
    # 작업이 끝난 뒤 최종 결과를 담는 payload.
    # API 응답, 후속 처리, 디버깅에서 최종 산출물을 재사용할 수 있게 한다.
    result_payload: dict[str, Any] = field(default_factory=dict)
    # Hermes식 todo/task list 의 canonical 상태.
    # step detail 안쪽 planning patch 와 별도로, task 단위에서 다음 작업 목록을 유지한다.
    todo_state: dict[str, Any] = field(default_factory=dict)
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
