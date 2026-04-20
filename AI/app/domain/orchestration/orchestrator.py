from __future__ import annotations

from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus
from app.core.utils.ids import new_id
from app.domain.tasks.models import StepRun, TaskRun
from app.flows.stub.approval_wait_flow import ApprovalWaitFlow
from app.flows.stub.echo_flow import EchoFlow


class Orchestrator:
    """요청을 flow 로 라우팅하고 초기 TaskRun, StepRun 을 만든다."""

    def __init__(self) -> None:
        self._flows = {
            EchoFlow.flow_name: EchoFlow(),
            ApprovalWaitFlow.flow_name: ApprovalWaitFlow(),
        }

    def plan(self, *, flow_name: str, owner_key: str, input_payload: dict) -> tuple[TaskRun, StepRun, object]:
        if flow_name not in self._flows:
            raise KeyError(flow_name)
        flow = self._flows[flow_name]
        task = TaskRun(
            task_run_id=new_id("task"),
            task_type=flow.task_type,
            flow_name=flow.flow_name,
            owner_key=owner_key,
            status=TaskStatus.PENDING,
            input_payload=input_payload,
        )
        step = StepRun(
            step_run_id=new_id("step"),
            task_run_id=task.task_run_id,
            step_order=1,
            step_type=flow.step_type,
            status=StepStatus.PENDING,
            input_payload=input_payload,
        )
        return task, step, flow
