from __future__ import annotations

from app.domain.orchestration.contracts import ORCHESTRATION_DETAIL_KEY, OrchestrationRequest
from app.domain.tasks.models import StepRun, TaskRun


class RouteDecider:
    """초기 route 선택과 resume 시 active route 복원을 담당한다."""

    def decide_initial_route(self, *, request: OrchestrationRequest) -> str:
        if request.requested_route:
            return request.requested_route
        if request.input_payload.get("route"):
            return str(request.input_payload["route"])
        return "model_generate_flow"

    def decide_resume_route(self, *, task: TaskRun, current_step: StepRun) -> str:
        orchestration = (current_step.detail_json or {}).get(ORCHESTRATION_DETAIL_KEY, {})
        return str(orchestration.get("activeRoute") or task.flow_name)
