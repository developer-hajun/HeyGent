from __future__ import annotations

from app.contracts.task.task_status import TaskStatus
from app.domain.tasks.repository import TaskRepository
from app.domain.tasks.runtime.task_run import TaskRun


class TaskService:
    """TaskRun 조회와 단순 갱신을 담당한다."""

    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository

    def get_task_or_raise(self, task_run_id: str) -> TaskRun:
        task = self.repository.get_task(task_run_id)
        if task is None:
            raise KeyError(task_run_id)
        return task

    def mark_waiting(self, task: TaskRun, wait_payload: dict, summary: str) -> TaskRun:
        task.status = TaskStatus.WAITING
        task.wait_payload = wait_payload
        task.progress_summary = summary
        task.revision += 1
        return self.repository.update_task(task)
