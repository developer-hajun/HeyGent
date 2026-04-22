from __future__ import annotations

from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus
from app.domain.capabilities.tools.contracts import CapabilitySpec


class EchoCapability:
    spec = CapabilitySpec(
        intent_type="stub.echo",
        entry_capability="stub.echo",
        executor_key="stub.echo",
        task_type="stub.echo",
        task_title="Echo 응답 태스크",
        step_type="echo.execute",
        step_title="입력 메시지 반영",
    )

    def execute(self, *, task, step, resume_payload=None):
        """입력 payload 를 그대로 result 로 돌려준다."""

        return {
            "task_status": TaskStatus.COMPLETED,
            "step_status": StepStatus.COMPLETED,
            "result_payload": {"echo": task.input_payload},
            "output_payload": {"echo": task.input_payload},
            "detail_json": {
                "agentDetail": {"called": False, "agentId": None, "childTaskRunId": None},
                "toolDetail": {"toolNames": [], "primaryTool": None},
                "llmDetail": {"model": None, "callCount": 0},
            },
            "summary_message": "echo capability completed",
        }
