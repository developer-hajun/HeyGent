from __future__ import annotations

import json

from app.domain.tasks.runtime import TaskRun


def summarize_child_task(task: TaskRun, summary_prompt: str | None) -> str | None:
    if task.progress_summary:
        return task.progress_summary
    if isinstance(task.result_payload.get("text"), str):
        return task.result_payload["text"]
    if task.result_payload:
        rendered = json.dumps(task.result_payload, ensure_ascii=False)
        if summary_prompt:
            return f"{summary_prompt}: {rendered}"
        return rendered
    return summary_prompt
