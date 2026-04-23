from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.domain.tasks.detail.step_detail import build_default_step_detail


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
    # 실제 실행자를 식별하는 키.
    # flow/route 를 지운 뒤에도 "어느 capability executor 가 이 step 을 돌렸는가"를 복원하려면 step 단위 실행자 식별자가 필요하다.
    executor_key: str | None = None
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
