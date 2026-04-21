from __future__ import annotations

from app.domain.orchestration.flow_router import FlowRouter
from app.domain.orchestration.planner import Planner
from app.domain.tasks.models import StepRun, TaskRun


class Orchestrator:
    """요청을 flow 로 라우팅하고 초기 TaskRun, StepRun 을 만든다."""

    def __init__(self, flow_router: FlowRouter, planner: Planner | None = None) -> None:
        self.flow_router = flow_router
        self.planner = planner or Planner()

    def plan(self, *, flow_name: str, owner_key: str, input_payload: dict) -> tuple[TaskRun, StepRun, object]:
        flow = self.flow_router.get(flow_name)
        planned_task = self.planner.create_task_plan(
            flow_name=flow.flow_name,
            task_type=flow.task_type,
            owner_key=owner_key,
            input_payload=input_payload,
            step_type=flow.step_type,
            task_title=getattr(flow, "task_title", flow.task_type),
            step_title=getattr(flow, "step_title", flow.step_type),
        )
        task, step = self.planner.materialize(planned_task)
        return task, step, flow

    def get_flow(self, flow_name: str):
        return self.flow_router.get(flow_name)

    def list_flows(self) -> list[str]:
        return self.flow_router.list_flows()
