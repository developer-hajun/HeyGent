from __future__ import annotations

from app.domain.execution.task_engine import TaskEngine
from app.domain.orchestration.contracts import OrchestrationRequest
from app.domain.orchestration.planner import Planner
from app.domain.orchestration.result_inspector import ResultInspector
from app.domain.orchestration.route_decider import RouteDecider
from app.domain.orchestration.worker_registry import WorkerRegistry
from app.domain.tasks.models import TaskRun
from app.domain.tasks.repository import TaskRepository


class Orchestrator:
    """main orchestration loop 을 제어한다."""

    def __init__(
        self,
        route_decider: RouteDecider,
        worker_registry: WorkerRegistry,
        planner: Planner,
        result_inspector: ResultInspector,
        task_engine: TaskEngine,
        repository: TaskRepository,
        max_handoffs: int = 3,
    ) -> None:
        self.route_decider = route_decider
        self.worker_registry = worker_registry
        self.planner = planner
        self.result_inspector = result_inspector
        self.task_engine = task_engine
        self.repository = repository
        self.max_handoffs = max_handoffs

    async def start(self, request: OrchestrationRequest) -> TaskRun:
        route = self.route_decider.decide_initial_route(request=request)
        worker = self.worker_registry.get(route)
        planned_task = self.planner.create_initial_plan(
            route=route,
            worker=worker,
            owner_key=request.owner_key,
            input_payload=request.input_payload,
        )
        task = self.planner.materialize_task(planned_task)
        step = self.planner.materialize_initial_step(task=task, planned_task=planned_task)
        task = await self.task_engine.run(task=task, step=step, flow=worker)
        return await self._run_loop(task=task)

    async def resume(self, *, task_run_id: str, approval_id: str, payload: dict) -> TaskRun:
        task = self.repository.get_task(task_run_id)
        if task is None:
            raise KeyError(task_run_id)
        approval = self.repository.get_open_approval(task_run_id)
        if approval is None:
            raise ValueError("no open approval")
        resolved_approval_id = approval_id or approval["approval_id"]
        current_step = self.repository.list_steps(task.task_run_id)[-1]
        route = self.route_decider.decide_resume_route(task=task, current_step=current_step)
        worker = self.worker_registry.get(route)
        task = await self.task_engine.resume(task=task, flow=worker, approval_id=resolved_approval_id, payload=payload)
        return await self._run_loop(task=task)

    async def _run_loop(self, *, task: TaskRun) -> TaskRun:
        handoff_count = 0
        while True:
            current_step = self.repository.list_steps(task.task_run_id)[-1]
            inspection = self.result_inspector.inspect(task=task, step=current_step)

            if inspection.next_action in {"done", "ask_user", "fail"}:
                return task
            if inspection.next_action != "handoff":
                return task
            if handoff_count >= self.max_handoffs:
                return task
            if not inspection.handoff_to:
                return task

            next_route = inspection.handoff_to
            next_worker = self.worker_registry.get(next_route)
            next_step = self.planner.create_handoff_step(
                task=task,
                route=next_route,
                worker=next_worker,
                input_payload=inspection.next_input_payload,
                step_order=len(self.repository.list_steps(task.task_run_id)) + 1,
            )
            task = await self.task_engine.run_next_step(task=task, step=next_step, flow=next_worker)
            handoff_count += 1

    def list_flows(self) -> list[str]:
        return self.worker_registry.list_routes()
