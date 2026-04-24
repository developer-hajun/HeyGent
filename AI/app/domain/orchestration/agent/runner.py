from __future__ import annotations

from app.tools.registry import ToolRegistry
from app.domain.orchestration.contracts import OrchestrationRequest
from app.domain.orchestration.agent.loop import TaskEngine
from app.domain.orchestration.policies import decide_executor_step_boundary
from app.domain.orchestration.runtime_planning import Planner
from app.domain.orchestration.resume import ResumeTargetResolver
from app.domain.tasks.repository import TaskRepository
from app.domain.tasks.models import TaskRun


class AgentLoopRunner:
    """Entry point that materializes TaskRun/StepRun and executes the agent loop."""

    def __init__(
        self,
        *,
        repository: TaskRepository,
        planner: Planner,
        task_engine: TaskEngine,
        tool_registry: ToolRegistry,
    ) -> None:
        self.repository = repository
        self.planner = planner
        self.task_engine = task_engine
        self.tool_registry = tool_registry
        self.resume_target_resolver = ResumeTargetResolver()

    async def start(self, request: OrchestrationRequest) -> TaskRun:
        executor = self.tool_registry.resolve(
            intent_type=request.intent_type,
            entry_executor_key=request.entry_executor_key,
        )
        task = self.planner.materialize_task(
            owner_key=request.owner_key,
            session_key=request.session_key,
            input_payload=request.input_payload,
            executor=executor,
        )
        boundary = decide_executor_step_boundary(
            current_detail=None,
            next_semantic_key=executor.spec.semantic_key or executor.spec.step_type,
        )
        if boundary.action != "create_new_step":
            raise ValueError(f"unexpected start boundary decision: {boundary.reason}")
        step = self.planner.materialize_step(
            task=task,
            executor=executor,
            input_payload=request.input_payload,
            step_order=1,
        )
        return await self.task_engine.run(task=task, step=step, executor=executor)

    async def resume(self, *, task: TaskRun, approval_id: str, payload: dict) -> TaskRun:
        open_approval = self.repository.get_open_approval(task.task_run_id)
        step_run_id = self.resume_target_resolver.resolve(task=task, open_approval=open_approval)

        step = self.repository.get_step(step_run_id)
        if step is None:
            raise KeyError(step_run_id)

        executor_key = step.executor_key or task.entry_executor_key
        if not executor_key:
            raise ValueError("step executor key is missing")

        executor = self.tool_registry.get(executor_key)
        boundary = decide_executor_step_boundary(
            current_detail=step.detail_json,
            next_semantic_key=executor.spec.semantic_key or step.step_type,
            is_resume=True,
        )
        if boundary.action != "reuse_for_resume":
            raise ValueError(f"unexpected resume boundary decision: {boundary.reason}")
        self.planner.materialize_resume_step(task=task, step=step, executor=executor)
        return await self.task_engine.resume(task=task, executor=executor, approval_id=approval_id, payload=payload)

    async def cancel_waiting(self, *, task: TaskRun) -> TaskRun:
        return await self.task_engine.cancel_waiting(task=task)

    async def start_child(
        self,
        *,
        owner_key: str,
        session_key: str | None,
        input_payload: dict,
        intent_type: str,
        entry_executor_key: str,
    ) -> TaskRun:
        return await self.start(
            OrchestrationRequest(
                owner_key=owner_key,
                session_key=session_key,
                input_payload=input_payload,
                intent_type=intent_type,
                entry_executor_key=entry_executor_key,
            )
        )
