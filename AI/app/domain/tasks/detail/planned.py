from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PlannedStep:
    """legacy placeholder.

    기존 planner 테스트 호환을 위해 남겨 두지만, canonical loop 는 더 이상 이 구조를 사용하지 않는다.
    """

    step_type: str
    title: str | None = None
    input_payload: dict[str, Any] = field(default_factory=dict)
    detail_json: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PlannedTask:
    """legacy placeholder.

    flow 중심 계획 스키마는 제거 대상이므로, 새 loop 에서는 사용하지 않는다.
    """

    task_type: str
    intent_type: str
    entry_capability: str
    owner_key: str
    title: str | None = None
    input_payload: dict[str, Any] = field(default_factory=dict)
    steps: list[PlannedStep] = field(default_factory=list)
