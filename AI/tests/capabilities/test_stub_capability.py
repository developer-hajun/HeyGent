from app.domain.capabilities.tools.stub.approval_wait import ApprovalWaitCapability
from app.domain.capabilities.tools.stub.echo import EchoCapability


def test_echo_capability_returns_input_payload(task_run, step_run):
    outcome = EchoCapability().execute(task=task_run, step=step_run)

    assert outcome["result_payload"]["echo"] == task_run.input_payload
    assert outcome["task_status"] == "COMPLETED"
    assert outcome["detail_json"]["llmDetail"]["callCount"] == 0


def test_approval_wait_capability_waits_then_completes(task_run, step_run):
    capability = ApprovalWaitCapability()

    waiting = capability.execute(task=task_run, step=step_run)
    completed = capability.execute(task=task_run, step=step_run, resume_payload={"approved": True})

    assert waiting["task_status"] == "WAITING"
    assert waiting["approval_payload"]["action"] == "approve"
    assert waiting["detail_json"]["agentDetail"]["called"] is False
    assert completed["result_payload"]["approved"] is True
