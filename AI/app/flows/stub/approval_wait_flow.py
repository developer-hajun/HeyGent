from __future__ import annotations

from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus


class ApprovalWaitFlow:
    flow_name = "approval_wait_flow"
    task_type = "stub.approval_wait"
    step_type = "approval.wait"
    task_title = "승인 대기 태스크"
    step_title = "승인 여부 확인"

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
                    "toolDetail": {"toolNames": [], "primaryTool": None},
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
                "toolDetail": {"toolNames": [], "primaryTool": None},
                "llmDetail": {"model": None, "callCount": 0},
            },
            "summary_message": "approval completed",
        }
