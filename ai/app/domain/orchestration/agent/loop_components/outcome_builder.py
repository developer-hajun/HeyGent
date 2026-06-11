"""결과 빌드 관련 컴포넌트.

ToolCallingLoop의 결과 빌드 관련 메서드들을 위임받는 thin adapter다.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.domain.orchestration.agent.tool_calling_loop import ToolCallingLoop


class OutcomeBuilder:
    """결과 빌드 관련 컴포넌트."""

    def __init__(self, loop: "ToolCallingLoop") -> None:
        self._loop = loop

    def build_completed_outcome(self, **kwargs: Any) -> dict[str, Any]:
        return self._loop._build_completed_outcome(**kwargs)

    def build_waiting_outcome(self, **kwargs: Any) -> dict[str, Any]:
        return self._loop._build_waiting_outcome(**kwargs)

    def build_failed_outcome(self, **kwargs: Any) -> dict[str, Any]:
        return self._loop._build_failed_outcome(**kwargs)

    def build_circuit_blocked_outcome(self, **kwargs: Any) -> dict[str, Any]:
        return self._loop._build_circuit_blocked_outcome(**kwargs)

    def build_provider_failure_outcome(self, **kwargs: Any) -> dict[str, Any]:
        return self._loop._build_provider_failure_outcome(**kwargs)
