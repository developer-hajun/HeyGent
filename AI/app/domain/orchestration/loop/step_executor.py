from __future__ import annotations


class StepExecutor:
    """개별 StepRun 실행을 capability executor 에 위임한다."""

    def execute(self, *, handler, task, step, resume_payload=None) -> dict:
        return handler.execute(task=task, step=step, resume_payload=resume_payload)
