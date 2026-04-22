from __future__ import annotations

from copy import deepcopy
from typing import Any


# StepRun detail 은 v1 에서 별도 invocation 테이블 대신 한 곳에 모아 둔다.
# 나중에 tool / agent / llm 계층을 분리하더라도 이 구조를 기준점으로 삼을 수 있게
# 키 이름을 먼저 고정해 둔다.
DEFAULT_STEP_DETAIL: dict[str, Any] = {
    "agentDetail": {
        # 다른 agent 를 실제로 호출했는지 여부.
        # 단순 LLM 호출과 agent orchestration 을 구분하려고 필요하다.
        "called": False,
        # 호출한 agent 의 식별자.
        # 어떤 agent 에 위임됐는지 추적해야 디버깅과 상세 화면 연결이 가능하다.
        "agentId": None,
        # agent 호출이 별도 child task 를 만들었다면 그 TaskRun ID.
        # 부모 step 에서 자식 task 로 이어지는 관계를 복원하려고 저장한다.
        "childTaskRunId": None,
    },
    "toolDetail": {
        # 사용한 tool 이름 목록.
        # 한 step 안에서 어떤 외부 도구를 건드렸는지 빠르게 파악할 수 있다.
        "toolNames": [],
        # 가장 핵심적으로 사용한 대표 tool 이름.
        # 목록이 길어질 때 UI 한 줄 요약용으로 쓰기 좋다.
        "primaryTool": None,
    },
    "llmDetail": {
        # 사용한 모델명.
        # 결과 품질/비용/재현성 이슈가 생겼을 때 모델 단위 추적이 필요하다.
        "model": None,
        # 해당 step 에서 LLM 을 몇 번 호출했는지 카운트.
        # 재시도나 다중 호출 여부를 파악해 비용/지연 분석에 쓴다.
        "callCount": 0,
    },
}


def build_default_step_detail() -> dict[str, Any]:
    """StepRun 이 기본적으로 가져야 하는 detail 구조를 만든다.

    deepcopy 를 쓰는 이유는 dataclass default 로 같은 dict 인스턴스가 재사용되면
    다른 step 의 detail 이 섞일 수 있기 때문이다.
    """

    return deepcopy(DEFAULT_STEP_DETAIL)


def merge_step_detail(current: dict[str, Any] | None, patch: dict[str, Any] | None) -> dict[str, Any]:
    """StepRun detail 에 부분 patch 를 합친다.

    v1 에서는 detailJson 을 StepRun 아래에 보관하기 때문에,
    loop 실행 중 계산된 일부 정보만 덮어쓸 수 있게 얕은-중첩 merge 를 제공한다.
    """

    merged = build_default_step_detail()
    for source in [current or {}, patch or {}]:
        for key, value in source.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = {**merged[key], **value}
            else:
                merged[key] = value
    return merged
