from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from app.domain.execution.task_engine import TaskEngine
from app.domain.tasks.repository import TaskRepository
from app.domain.tasks.service import TaskService


@dataclass(slots=True)
class TaskContext:
    """라우터에서 task 관련 의존성을 한 번에 묶어 쓰기 위한 컨텍스트다."""

    repository: TaskRepository
    service: TaskService
    engine: TaskEngine


def get_task_context(request: Request) -> TaskContext:
    repository = request.app.state.repository
    return TaskContext(
        repository=repository,
        service=TaskService(repository),
        engine=request.app.state.task_engine,
    )
