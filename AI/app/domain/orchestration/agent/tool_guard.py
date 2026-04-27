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
        if task_input.get("approval_required") and not self._has_approved_global_resume(task_input):
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

    @staticmethod
    def _has_approved_global_resume(task_input: dict[str, Any]) -> bool:
        context = task_input.get("_approved_resume_context")
        if not isinstance(context, dict):
            return False
        # 전역 approval_required로 멈춘 TaskRun(사용자 요청 전체 실행)이 승인된 뒤에는
        # 같은 resume/replay 안의 후속 tool call이 같은 전역 조건으로 다시 WAITING에 빠지지 않게 한다.
        return bool(context.get("approved")) and context.get("source") == "legacy_input_payload"
