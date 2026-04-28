from __future__ import annotations

from dataclasses import dataclass

from app.tools.contracts import TaskExecutor


@dataclass(frozen=True, slots=True)
class ToolEntry:
    """agent.loop registry entry 에 필요한 실행 metadata 다."""

    name: str
    toolset: str
    executor: TaskExecutor
