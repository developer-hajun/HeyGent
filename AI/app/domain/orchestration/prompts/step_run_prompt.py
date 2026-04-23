from __future__ import annotations


def build_step_run_prompt(*, step_title: str) -> str:
    return f"현재 StepRun 규칙: {step_title}"
