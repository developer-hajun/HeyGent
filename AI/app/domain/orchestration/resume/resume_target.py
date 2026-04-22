from __future__ import annotations


class ResumeTargetResolver:
    """resume 시 붙잡아야 할 exact StepRun 을 결정한다."""

    def resolve(self, *, task, open_approval: dict | None) -> str:
        step_run_id = task.current_step_run_id or (open_approval or {}).get("step_run_id")
        if not step_run_id:
            raise ValueError("current waiting step is missing")
        return step_run_id
