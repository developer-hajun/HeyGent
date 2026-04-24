from __future__ import annotations

from dataclasses import dataclass

from app.tools.contracts import TaskExecutor


@dataclass(frozen=True, slots=True)
class ToolEntry:
    """Tool registry entry aligned with Hermes-style tool metadata."""

    name: str
    toolset: str
    executor: TaskExecutor
