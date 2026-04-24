from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class OrchestrationRequest:
    """오케스트레이터 시작 입력을 한 곳으로 모은다.

    flow 제거 이후에는 `intent_type` 과 `entry_executor_key` 만으로 진입점을 설명한다.
    entry executor 를 주지 않으면 registry 가 intent 기준 default executor 를 선택한다.
    """

    owner_key: str
    input_payload: dict[str, Any]
    intent_type: str | None = None
    entry_executor_key: str | None = None
    # Deprecated 호환 입력. 내부 기준은 entry_executor_key 다.
    entry_capability: str | None = None


ORCHESTRATION_DETAIL_KEY = "orchestration"


def build_orchestration_detail(*, intent_type: str, entry_executor_key: str, executor_key: str, semantic_step: str) -> dict[str, Any]:
    return {
        ORCHESTRATION_DETAIL_KEY: {
            "intentType": intent_type,
            "entryExecutorKey": entry_executor_key,
            "executorKey": executor_key,
            "semanticStep": semantic_step,
        }
    }
