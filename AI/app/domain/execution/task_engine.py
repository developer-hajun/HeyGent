from __future__ import annotations

from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus
from app.core.time import utc_now
from app.domain.approvals.service import ApprovalService
from app.domain.execution.state_machine import ensure_step_transition, ensure_task_transition
from app.domain.execution.step_executor import StepExecutor
from app.domain.gateway.broadcaster import EventBroadcaster
from app.domain.tasks.events import build_task_event
from app.domain.tasks.models import StepRun, TaskRun
from app.domain.tasks.repository import TaskRepository
from app.domain.tasks.step_detail import merge_step_detail


class TaskEngine:
    """TaskRun 실행, waiting, resume 를 한 곳에서 조정한다."""

    def __init__(self, repository: TaskRepository, broadcaster: EventBroadcaster, approval_service: ApprovalService) -> None:
        self.repository = repository
        self.broadcaster = broadcaster
        self.approval_service = approval_service
        self.step_executor = StepExecutor()

    async def run(self, *, task: TaskRun, step: StepRun, flow) -> TaskRun:
        self.repository.create_task(task)
        self.repository.create_step(step)
        await self._emit("task.created", task)
        await self._emit("step.created", task, step)
        return await self._execute(task=task, step=step, flow=flow, resume_payload=None)

    async def resume(self, *, task: TaskRun, flow, approval_id: str, payload: dict) -> TaskRun:
        approval = self.approval_service.resolve(approval_id, payload)
        if approval is None:
            raise KeyError(approval_id)
        step = self.repository.list_steps(task.task_run_id)[0]
        await self._emit("approval.resolved", task, step, payload={"approval_id": approval_id, **payload})
        return await self._execute(task=task, step=step, flow=flow, resume_payload=payload)

    async def _execute(self, *, task: TaskRun, step: StepRun, flow, resume_payload: dict | None) -> TaskRun:
        ensure_task_transition(task.status, TaskStatus.RUNNING)
        ensure_step_transition(step.status, StepStatus.RUNNING)
        task.status = TaskStatus.RUNNING
        task.started_at = task.started_at or utc_now()
        task.wait_payload = {}
        step.status = StepStatus.RUNNING
        step.started_at = step.started_at or utc_now()
        self.repository.update_task(task)
        self.repository.update_step(step)
        await self._emit("task.started", task)
        await self._emit("step.started", task, step)

        outcome = self.step_executor.execute(handler=flow, task=task, step=step, resume_payload=resume_payload)
        return await self._apply_outcome(task=task, step=step, outcome=outcome)

    async def _apply_outcome(self, *, task: TaskRun, step: StepRun, outcome: dict) -> TaskRun:
        task_status = outcome["task_status"]
        step_status = outcome["step_status"]
        ensure_task_transition(task.status, task_status)
        ensure_step_transition(step.status, step_status)

        task.status = task_status
        step.status = step_status
        task.result_payload = outcome.get("result_payload", task.result_payload)
        task.wait_payload = outcome.get("wait_payload", {})
        task.progress_summary = outcome.get("summary_message")
        task.revision += 1
        step.output_payload = outcome.get("output_payload", step.output_payload)
        step.wait_payload = outcome.get("wait_payload", {})
        step.detail_json = merge_step_detail(step.detail_json, outcome.get("detail_json"))
        step.summary_message = outcome.get("summary_message")
        if task_status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED}:
            task.ended_at = utc_now()
            step.ended_at = utc_now()
        self.repository.update_task(task)
        self.repository.update_step(step)

        if task_status == TaskStatus.WAITING:
            approval = self.approval_service.request(task_run_id=task.task_run_id, step_run_id=step.step_run_id, payload=outcome.get("approval_payload", {}))
            await self._emit("approval.requested", task, step, payload=approval)
            await self._emit("task.waiting", task, step)
            await self._emit("step.waiting", task, step)
            return task

        if task_status == TaskStatus.COMPLETED:
            await self._emit("step.completed", task, step)
            await self._emit("task.completed", task, step, payload=task.result_payload)
            return task

        await self._emit("task.updated", task, step)
        return task

    async def _emit(self, event_type: str, task: TaskRun, step: StepRun | None = None, payload: dict | None = None) -> None:
        event = build_task_event(
            event_type=event_type,
            task_run_id=task.task_run_id,
            step_run_id=step.step_run_id if step else None,
            producer="task_engine",
            status=task.status,
            summary_message=task.progress_summary,
            payload=payload or {},
        )
        self.repository.append_event(event)
        await self.broadcaster.publish(event)
