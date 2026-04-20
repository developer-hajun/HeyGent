from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PlannedStep:
    """Orchestrator 가 만든 실행 계획 한 줄이다."""

    step_type: str
    input_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PlannedTask:
    """Flow 결정 결과를 execution 계층에 넘기기 위한 내부 스키마다."""

    flow_name: str
    task_type: str
    owner_key: str
    input_payload: dict[str, Any] = field(default_factory=dict)
    steps: list[PlannedStep] = field(default_factory=list)
