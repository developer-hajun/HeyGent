from __future__ import annotations


class StepHandler:
    """Delegate the concrete step body to the selected handler."""

    def execute(self, *, handler, task, step, resume_payload=None) -> dict:
        return handler.execute(task=task, step=step, resume_payload=resume_payload)
