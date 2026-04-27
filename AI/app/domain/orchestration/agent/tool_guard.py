from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ToolGuardDecision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    NEEDS_APPROVAL = "NEEDS_APPROVAL"


@dataclass(frozen=True, slots=True)
class ToolGuardResult:
    decision: ToolGuardDecision
    reason: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            **dict(self.payload or {}),
            "decision": self.decision.value,
            "reason": self.reason,
        }


class ToolGuard:
    """agent.loop가 runtime tool 실행 직전에 적용하는 최소 정책 계층이다.

    runtime tool은 agent.loop 안에서 LLM이 호출할 수 있는 실제 기능이다.
    """

    def evaluate(
        self,
        *,
        task_input: dict[str, Any],
        tool_call_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ToolGuardResult:
        if task_input.get("approval_required"):
            # approval은 도구 실행 전 사용자 확인이 필요한 상태로, 실제 실행은 resume 이후로 미룬다.
            reason = str(task_input.get("approval_reason") or f"{tool_name} 실행 전 승인이 필요합니다")
            return ToolGuardResult(
                decision=ToolGuardDecision.NEEDS_APPROVAL,
                reason=reason,
                payload={
                    "required": True,
                    "source": "legacy_input_payload",
                    "tool_call_id": tool_call_id,
                    "tool_name": tool_name,
                },
            )
        return ToolGuardResult(decision=ToolGuardDecision.ALLOW)
