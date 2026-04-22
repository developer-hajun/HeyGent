from __future__ import annotations

from app.domain.orchestration.contracts import OrchestrationRequest
from app.domain.orchestration.loop.runner import AgentLoopRunner
from app.domain.tasks.repository import TaskRepository
from app.domain.tasks.runtime import TaskRun


class Orchestrator:
    """요청과 resume 를 loop runner 로 넘기는 얇은 진입점이다."""

    def __init__(self, loop_runner: AgentLoopRunner, repository: TaskRepository) -> None:
        self.loop_runner = loop_runner
        self.repository = repository

    async def start(self, request: OrchestrationRequest) -> TaskRun:
        return await self.loop_runner.start(request)

    async def resume(self, *, task_run_id: str, approval_id: str, payload: dict) -> TaskRun:
        task = self.repository.get_task(task_run_id)
        if task is None:
            raise KeyError(task_run_id)
        approval = self.repository.get_open_approval(task_run_id)
        if approval is None:
            raise ValueError("no open approval")
        resolved_approval_id = approval_id or approval["approval_id"]
        task.current_step_run_id = approval["step_run_id"]
        return await self.loop_runner.resume(task=task, approval_id=resolved_approval_id, payload=payload)
