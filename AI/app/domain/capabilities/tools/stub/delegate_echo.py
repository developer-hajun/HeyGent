from __future__ import annotations

from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus
from app.domain.capabilities.tools.contracts import CapabilitySpec


class DelegateEchoCapability:
    spec = CapabilitySpec(
        intent_type="stub.delegate_echo",
        entry_capability="stub.delegate_echo",
        executor_key="stub.delegate_echo",
        task_type="stub.delegate_echo",
        task_title="Child 위임 태스크",
        step_type="delegate.child",
        step_title="Child Echo 위임",
        semantic_key="delegate.child.echo",
        semantic_goal="부모 StepRun 에서 child task 를 독립 세션으로 실행하고 결과를 회수한다.",
    )

    def execute(self, *, task, step, resume_payload=None):
        """child session runtime 을 통해 stub.echo task 를 별도 TaskRun 으로 띄운다."""

        child_message = str(task.input_payload.get("message", "")).strip() or "child echo"
        return {
            "task_status": TaskStatus.COMPLETED,
            "step_status": StepStatus.COMPLETED,
            "result_payload": {"delegated": True, "requestedChildMessage": child_message},
            "output_payload": {"delegated": True},
            "detail_json": {
                "toolDetail": {"toolNames": ["agent.delegate"], "primaryTool": "agent.delegate"},
                "llmDetail": {"model": None, "callCount": 0},
            },
            "summary_message": "child delegation completed",
            "child_session": {
                "intent_type": "stub.echo",
                "entry_capability": "stub.echo",
                "input_payload": {"message": child_message},
                "summary_prompt": "child echo 결과",
                "metadata": {"delegationKind": "echo"},
            },
        }
