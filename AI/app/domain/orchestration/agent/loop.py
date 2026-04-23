from __future__ import annotations

from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus
from app.core.time import utc_now
from app.domain.orchestration.agent.step_executor import StepExecutor
from app.domain.orchestration.approval import ApprovalRuntime, ApprovalService
from app.domain.orchestration.delegation import ChildSessionLauncher, DelegateRuntime
from app.domain.orchestration.policies import ensure_step_transition, ensure_task_transition, normalize_executor_outcome
from app.domain.orchestration.result_inspector import OutcomeInspector
from app.domain.tasks.detail import build_semantic_step_detail, merge_step_detail
from app.domain.tasks.events import build_task_event
from app.domain.tasks.repository import TaskRepository
from app.domain.tasks.runtime import StepRun, TaskRun


class TaskEngine:
    """Coordinate task execution, approval waiting, and exact-step resume."""

    def __init__(
        self,
        repository: TaskRepository,
        broadcaster,
        approval_service: ApprovalService,
        child_session_launcher: ChildSessionLauncher,
    ) -> None:
        self.repository = repository
        self.broadcaster = broadcaster
        self.approval_service = approval_service
        self.child_session_launcher = child_session_launcher
        self.approval_runtime = ApprovalRuntime()
        self.delegate_runtime = DelegateRuntime(child_session_launcher)
        self.outcome_inspector = OutcomeInspector()
        self.step_executor = StepExecutor()

    async def run(self, *, task: TaskRun, step: StepRun, executor) -> TaskRun:
        task.current_step_run_id = step.step_run_id
        self.repository.create_task(task)
        self.repository.create_step(step)
        await self._emit("task.created", task)
        await self._emit("step.created", task, step)
        return await self._execute(task=task, step=step, executor=executor, resume_payload=None)

    async def resume(self, *, task: TaskRun, executor, approval_id: str, payload: dict) -> TaskRun:
        approval = self.approval_service.resolve(approval_id, payload)
        if approval is None:
            raise KeyError(approval_id)

        step = self.repository.get_step(approval["step_run_id"])
        if step is None:
            raise KeyError(approval["step_run_id"])
        task.current_step_run_id = step.step_run_id
        self.approval_runtime.mark_resolved_step(step=step, approval_id=approval_id, response_payload=payload)
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_semantic_step_detail(
                step_run_id=step.step_run_id,
                semantic_key=(step.detail_json.get("semanticDetail") or {}).get("semanticKey") or step.step_type,
                semantic_step=(step.detail_json.get("semanticDetail") or {}).get("semanticStep") or step.title or step.step_type,
                semantic_goal=(step.detail_json.get("semanticDetail") or {}).get("goal") or step.title or step.step_type,
                lifecycle="resuming",
            ),
        )
        self.repository.update_step(step)
        await self._emit("approval.resolved", task, step, payload={"approval_id": approval_id, **payload})
        return await self._execute(task=task, step=step, executor=executor, resume_payload=payload)

    async def _execute(self, *, task: TaskRun, step: StepRun, executor, resume_payload: dict | None) -> TaskRun:
        ensure_task_transition(task.status, TaskStatus.RUNNING)
        ensure_step_transition(step.status, StepStatus.RUNNING)

        task.status = TaskStatus.RUNNING
        task.started_at = task.started_at or utc_now()
        task.wait_payload = {}
        task.current_step_run_id = step.step_run_id
        step.status = StepStatus.RUNNING
        step.started_at = step.started_at or utc_now()
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_semantic_step_detail(
                step_run_id=step.step_run_id,
                semantic_key=(step.detail_json.get("semanticDetail") or {}).get("semanticKey") or executor.spec.semantic_key or step.step_type,
                semantic_step=(step.detail_json.get("semanticDetail") or {}).get("semanticStep") or step.title or executor.spec.step_title,
                semantic_goal=(step.detail_json.get("semanticDetail") or {}).get("goal") or executor.spec.semantic_goal or step.title or executor.spec.step_title,
                lifecycle="running",
            ),
        )
        self.repository.update_task(task)
        self.repository.update_step(step)
        await self._emit("task.started", task)
        await self._emit("step.started", task, step)

        outcome = normalize_executor_outcome(
            self.step_executor.execute(handler=executor, task=task, step=step, resume_payload=resume_payload)
        )
        return await self._apply_outcome(task=task, step=step, outcome=outcome)

    async def _apply_outcome(self, *, task: TaskRun, step: StepRun, outcome: dict) -> TaskRun:
        outcome = await self.delegate_runtime.apply(task=task, step=step, outcome=outcome, repository=self.repository)
        outcome = self.outcome_inspector.inspect(step=step, outcome=outcome)
        task_status = outcome["task_status"]
        step_status = outcome["step_status"]
        ensure_task_transition(task.status, task_status)
        ensure_step_transition(step.status, step_status)

        task.status = task_status
        step.status = step_status
        task.current_step_run_id = step.step_run_id
        task.result_payload = outcome.get("result_payload", task.result_payload)
        task.wait_payload = outcome.get("wait_payload", {})
        task.error_message = outcome.get("error_message")
        task.progress_summary = outcome.get("summary_message")
        task.revision += 1
        step.output_payload = outcome.get("output_payload", step.output_payload)
        step.wait_payload = outcome.get("wait_payload", {})
        step.error_message = outcome.get("error_message")
        step.detail_json = merge_step_detail(step.detail_json, outcome.get("detail_json"))
        step.detail_json = merge_step_detail(
            step.detail_json,
            build_semantic_step_detail(
                step_run_id=step.step_run_id,
                semantic_key=(step.detail_json.get("semanticDetail") or {}).get("semanticKey") or step.step_type,
                semantic_step=(step.detail_json.get("semanticDetail") or {}).get("semanticStep") or step.title or step.step_type,
                semantic_goal=(step.detail_json.get("semanticDetail") or {}).get("goal") or step.title or step.step_type,
                lifecycle=self._semantic_lifecycle(task_status),
            ),
        )
        step.summary_message = outcome.get("summary_message")
        if task_status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED}:
            task.ended_at = utc_now()
            step.ended_at = utc_now()
        self.repository.update_task(task)
        self.repository.update_step(step)

        if task_status == TaskStatus.WAITING:
            approval = self.approval_service.request(
                task_run_id=task.task_run_id,
                step_run_id=step.step_run_id,
                payload=outcome.get("approval_payload", {}),
            )
            self.approval_runtime.attach_waiting_approval(task=task, step=step, approval=approval)
            self.repository.update_task(task)
            self.repository.update_step(step)
            await self._emit("approval.requested", task, step, payload=approval)
            await self._emit("task.waiting", task, step)
            await self._emit("step.waiting", task, step)
            return task

        if task_status == TaskStatus.COMPLETED:
            await self._emit("step.completed", task, step)
            await self._emit("task.completed", task, step, payload=task.result_payload)
            return task

        if task_status == TaskStatus.FAILED:
            await self._emit("step.failed", task, step, payload={"error_message": step.error_message})
            await self._emit("task.failed", task, step, payload={"error_message": task.error_message})
            return task

        if task_status == TaskStatus.CANCELED:
            await self._emit("step.canceled", task, step)
            await self._emit("task.canceled", task, step)
            return task

        await self._emit("task.updated", task, step)
        return task

    @staticmethod
    def _semantic_lifecycle(task_status: str) -> str:
        if task_status == TaskStatus.WAITING:
            return "waiting"
        if task_status == TaskStatus.COMPLETED:
            return "completed"
        if task_status == TaskStatus.FAILED:
            return "failed"
        if task_status == TaskStatus.CANCELED:
            return "canceled"
        return "running"

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
