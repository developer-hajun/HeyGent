from __future__ import annotations

from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus


class EchoFlow:
    flow_name = "echo_flow"
    task_type = "stub.echo"
    step_type = "echo.execute"

    def execute(self, *, task, step, resume_payload=None):
        """입력 payload 를 그대로 result 로 돌려준다."""

        return {
            "task_status": TaskStatus.COMPLETED,
            "step_status": StepStatus.COMPLETED,
            "result_payload": {"echo": task.input_payload},
            "output_payload": {"echo": task.input_payload},
            "summary_message": "echo flow completed",
        }
