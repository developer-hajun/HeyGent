from __future__ import annotations


def build_step_context_prompt(*, step=None) -> str:
    if step is None:
        return ""
    return f"현재 StepRun: {step.step_run_id} ({step.status})"
