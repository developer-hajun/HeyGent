from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class OrchestrationRequest:
    """오케스트레이터 시작 입력을 한 곳으로 모은다."""

    owner_key: str
    session_key: str | None
    input_payload: dict[str, Any]
    task_run_id: str | None = None


ORCHESTRATION_DETAIL_KEY = "orchestration"


def build_orchestration_detail(*, semantic_step: str) -> dict[str, Any]:
    return {
        ORCHESTRATION_DETAIL_KEY: {
            "semanticStep": semantic_step,
        }
    }
