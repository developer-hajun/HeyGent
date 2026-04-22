from __future__ import annotations

from app.domain.capabilities.tools.registry import CapabilityRegistry
from app.domain.orchestration.contracts import OrchestrationRequest
from app.domain.orchestration.loop.task_engine import TaskEngine
from app.domain.orchestration.planning.planner import Planner
from app.domain.orchestration.resume import ResumeTargetResolver
from app.domain.tasks.repository import TaskRepository
from app.domain.tasks.runtime import TaskRun


class AgentLoopRunner:
    """flow 추론 없이 loop-first 로 TaskRun 을 시작하는 진입점이다."""

    def __init__(
        self,
        *,
        repository: TaskRepository,
        planner: Planner,
        task_engine: TaskEngine,
        capability_registry: CapabilityRegistry,
    ) -> None:
        self.repository = repository
        self.planner = planner
        self.task_engine = task_engine
        self.capability_registry = capability_registry
        self.resume_target_resolver = ResumeTargetResolver()

    async def start(self, request: OrchestrationRequest) -> TaskRun:
        executor = self.capability_registry.resolve(
            intent_type=request.intent_type,
            entry_capability=request.entry_capability,
        )
        task = self.planner.materialize_task(
            owner_key=request.owner_key,
            input_payload=request.input_payload,
            executor=executor,
        )
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

        executor_key = step.executor_key or task.entry_capability
        if not executor_key:
            raise ValueError("step executor key is missing")

        # waiting 에서 resume 로 넘어갈 때는 같은 StepRun 을 다시 잡아야 한다.
        # 새 step 를 만들면 approval/event/history 가 끊기므로, exact step 재사용을 강제한다.
        executor = self.capability_registry.get(executor_key)
        self.planner.materialize_resume_step(task=task, step=step, executor=executor)
        return await self.task_engine.resume(task=task, executor=executor, approval_id=approval_id, payload=payload)

    async def start_child(
        self,
        *,
        owner_key: str,
        input_payload: dict,
        intent_type: str,
        entry_capability: str,
    ) -> TaskRun:
        """child 세션도 flow 추론 없이 동일한 loop-first 진입점을 재사용한다."""

        return await self.start(
            OrchestrationRequest(
                owner_key=owner_key,
                input_payload=input_payload,
                intent_type=intent_type,
                entry_capability=entry_capability,
            )
        )
