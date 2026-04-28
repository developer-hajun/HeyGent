from __future__ import annotations

from app.contracts.task.task_status import TaskStatus


def child_task_unsuccessful(status: str) -> bool:
    return status in {TaskStatus.FAILED, TaskStatus.CANCELED}
