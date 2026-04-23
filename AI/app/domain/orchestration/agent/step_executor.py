from __future__ import annotations


class StepExecutor:
    """Delegate the concrete step body to the selected capability executor."""

    def execute(self, *, handler, task, step, resume_payload=None) -> dict:
        return handler.execute(task=task, step=step, resume_payload=resume_payload)
