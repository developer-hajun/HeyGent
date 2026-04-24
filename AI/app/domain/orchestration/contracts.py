from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class OrchestrationRequest:
    """오케스트레이터 시작 입력을 한 곳으로 모은다.

    flow 제거 이후에는 `intent_type` 과 호환 필드인 `entry_capability` 만으로 진입점을 설명한다.
    entry executor 를 주지 않으면 registry 가 intent 기준 default executor 를 선택한다.
    """

    owner_key: str
    input_payload: dict[str, Any]
    intent_type: str | None = None
    # TODO: 2차 migration 에서 entry_executor_key 로 바꾸고 API/DB 호환 alias 를 둔다.
    entry_capability: str | None = None


ORCHESTRATION_DETAIL_KEY = "orchestration"


def build_orchestration_detail(*, intent_type: str, entry_capability: str, executor_key: str, semantic_step: str) -> dict[str, Any]:
    return {
        ORCHESTRATION_DETAIL_KEY: {
            "intentType": intent_type,
            "entryCapability": entry_capability,
            "executorKey": executor_key,
            "semanticStep": semantic_step,
        }
    }
