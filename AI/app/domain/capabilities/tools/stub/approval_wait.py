from __future__ import annotations

from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus
from app.domain.capabilities.tools.contracts import CapabilitySpec


class ApprovalWaitCapability:
    spec = CapabilitySpec(
        intent_type="stub.approval_wait",
        entry_capability="stub.approval_wait",
        executor_key="stub.approval_wait",
        task_type="stub.approval_wait",
        task_title="승인 대기 태스크",
        step_type="approval.wait",
        step_title="사용자 승인 대기",
        semantic_key="approval.checkpoint",
        semantic_goal="사용자 승인 전까지 정확히 같은 StepRun 을 기준으로 대기하고 재개한다.",
    )

    def execute(self, *, task, step, resume_payload=None):
        """첫 실행에서는 WAITING 으로 멈추고, resume 이후 완료한다."""

        approved = bool((resume_payload or {}).get("approved"))
        if not approved:
            return {
                "task_status": TaskStatus.WAITING,
                "step_status": StepStatus.WAITING,
                "wait_payload": {"reason": "approval_required"},
                "detail_json": {
                    "agentDetail": {"called": False, "agentId": None, "childTaskRunId": None},
                    "toolDetail": {"toolNames": ["approval.request"], "primaryTool": "approval.request"},
                    "llmDetail": {"model": None, "callCount": 0},
                },
                "summary_message": "approval required",
                "approval_payload": {"reason": "echo 승인 확인", "action": "approve"},
            }

        return {
            "task_status": TaskStatus.COMPLETED,
            "step_status": StepStatus.COMPLETED,
            "result_payload": {"approved": True, "resume_payload": resume_payload or {}},
            "output_payload": {"approved": True},
            "detail_json": {
                "agentDetail": {"called": False, "agentId": None, "childTaskRunId": None},
                "toolDetail": {"toolNames": ["approval.resume"], "primaryTool": "approval.resume"},
                "llmDetail": {"model": None, "callCount": 0},
            },
            "summary_message": "approval completed",
        }
