from __future__ import annotations

from copy import deepcopy
from typing import Any


# StepRun detail 은 v1 에서 별도 invocation 테이블 대신 한 곳에 모아 둔다.
# 나중에 tool / agent / llm 계층을 분리하더라도 이 구조를 기준점으로 삼을 수 있게
# 키 이름을 먼저 고정해 둔다.
DEFAULT_STEP_DETAIL: dict[str, Any] = {
    "agentDetail": {
        "called": False,
        "agentId": None,
        "childTaskRunId": None,
    },
    "toolDetail": {
        "toolNames": [],
        "primaryTool": None,
    },
    "llmDetail": {
        "model": None,
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
    flow 가 반환한 일부 정보만 덮어쓸 수 있게 얕은-중첩 merge 를 제공한다.
    """

    merged = build_default_step_detail()
    for source in [current or {}, patch or {}]:
        for key, value in source.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = {**merged[key], **value}
            else:
                merged[key] = value
    return merged
