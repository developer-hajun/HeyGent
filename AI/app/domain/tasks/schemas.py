from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PlannedStep:
    """Orchestrator 가 만든 실행 계획 한 줄이다."""

    # 어떤 종류의 step 을 실행할지 나타내는 내부 타입명.
    # planner 가 만든 계획을 executor 가 해석하려면 이 값이 기준이 된다.
    step_type: str
    # 사람이 읽는 step 제목.
    # 계획 검토나 로그 확인 시 내부 타입명만 보는 것보다 이해가 쉽다.
    title: str | None = None
    # 이 step 에 넘길 입력 데이터.
    # 실행 전 계획 단계에서 이미 필요한 문맥을 확정해 두기 위해 저장한다.
    input_payload: dict[str, Any] = field(default_factory=dict)
    # 실행 전에 미리 붙여 둘 부가 메타데이터.
    # 실제 실행 상세(detail_json)와 달리, 이 값은 "계획 시점에 알고 있던 힌트"를 담는 용도다.
    detail_json: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PlannedTask:
    """Flow 결정 결과를 execution 계층에 넘기기 위한 내부 스키마다."""

    # 어떤 flow 로 실행할지 나타내는 내부 이름.
    # executor 가 올바른 flow 구현체를 선택하려면 필요하다.
    flow_name: str
    # 사용자가 요청한 작업 종류.
    # flow_name 과 분리해 두면 "요청 의미"와 "실행 구현"을 각각 추적할 수 있다.
    task_type: str
    # 사용자가 요청한 intent_type.
    # flow 제거 이후에는 TaskRun.task_type 과 별도로 canonical intent 기준점으로 유지한다.
    intent_type: str
    # 처음 진입할 capability 키.
    # route 대신 capability 기준으로 첫 실행자를 고정해 두려는 필드다.
    entry_capability: str
    # 작업 소유자/세션 범위를 구분하는 키.
    # 계획 단계에서부터 ownership 을 붙여 둬야 이후 저장 시 일관되게 흘러간다.
    owner_key: str
    # 사람이 읽기 쉬운 작업 제목.
    # task browser 나 로그에서 즉시 이해할 수 있는 라벨로 쓴다.
    title: str | None = None
    # Task 전체 입력값.
    # 계획을 세울 때 받은 원본 요청을 execution 으로 그대로 넘기기 위해 필요하다.
    input_payload: dict[str, Any] = field(default_factory=dict)
    # 이 Task 를 구성하는 step 계획 목록.
    # executor 는 이 리스트를 기반으로 실제 StepRun 들을 생성한다.
    steps: list[PlannedStep] = field(default_factory=list)
