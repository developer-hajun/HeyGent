from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from app.domain.orchestration.agent.loop import TaskEngine
from app.domain.tasks.repository import TaskRepository
from app.domain.tasks.runtime.service import TaskService
from app.storage.redis import RedisTaskProjectionStore


@dataclass(slots=True)
class TaskContext:
    """라우터에서 task 관련 의존성을 한 번에 묶어 쓰기 위한 컨텍스트다."""

    repository: TaskRepository
    service: TaskService
    engine: TaskEngine
    task_projection_store: RedisTaskProjectionStore | None = None


def get_task_context(request: Request) -> TaskContext:
    repository = request.app.state.repository
    return TaskContext(
        repository=repository,
        service=TaskService(repository),
        engine=request.app.state.task_engine,
        task_projection_store=getattr(request.app.state, "task_projection_store", None),
    )
