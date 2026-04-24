from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ChildSessionSpec:
    parent_task_run_id: str
    parent_step_run_id: str
    child_intent_type: str
    child_entry_executor_key: str
    summary_prompt: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ChildSessionLaunchResult:
    agent_id: str
    child_task_run_id: str
    status: str
    summary: str | None
