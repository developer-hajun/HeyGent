from __future__ import annotations


class StepPresenter:
    def present(self, step) -> str:
        return f"{step.title or step.step_type} [{step.status}]"
