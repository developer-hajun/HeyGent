from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ChildSessionSpec:
    """부모 step 이 자식 세션을 띄울 때 유지해야 하는 최소 연결 정보다."""

    parent_task_run_id: str
    parent_step_run_id: str
    child_intent_type: str
    child_entry_capability: str
    summary_prompt: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
