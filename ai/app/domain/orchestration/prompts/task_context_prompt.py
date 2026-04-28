from __future__ import annotations


def build_task_context_prompt(*, task=None, input_payload: dict | None = None) -> str:
    if task is None:
        return ""
    return f"현재 TaskRun: {task.task_run_id} ({task.status})"
