from __future__ import annotations

from app.contracts.task.task_status import TaskStatus


class InvalidResumeTargetError(ValueError):
    pass


class ResumeTargetResolver:
    """resume 시 붙잡아야 할 exact StepRun 을 결정한다."""

    def resolve(self, *, task, open_approval: dict | None) -> str:
        if task.status != TaskStatus.WAITING:
            raise InvalidResumeTargetError(f"task is not waiting: {task.status}")
        if open_approval is None:
            raise InvalidResumeTargetError("open approval is missing")

        approval_step_run_id = str(open_approval.get("step_run_id") or "").strip()
        current_step_run_id = str(task.current_step_run_id or "").strip()
        if not approval_step_run_id:
            raise InvalidResumeTargetError("approval step is missing")
        if current_step_run_id and current_step_run_id != approval_step_run_id:
            raise InvalidResumeTargetError(
                f"waiting step mismatch: task={current_step_run_id}, approval={approval_step_run_id}"
            )
        return approval_step_run_id
