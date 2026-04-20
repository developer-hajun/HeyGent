from app.flows.stub.approval_wait_flow import ApprovalWaitFlow
from app.flows.stub.echo_flow import EchoFlow


def test_echo_flow_returns_input_payload(task_run, step_run):
    outcome = EchoFlow().execute(task=task_run, step=step_run)

    assert outcome["result_payload"]["echo"] == task_run.input_payload
    assert outcome["task_status"] == "COMPLETED"


def test_approval_wait_flow_waits_then_completes(task_run, step_run):
    flow = ApprovalWaitFlow()

    waiting = flow.execute(task=task_run, step=step_run)
    completed = flow.execute(task=task_run, step=step_run, resume_payload={"approved": True})

    assert waiting["task_status"] == "WAITING"
    assert waiting["approval_payload"]["action"] == "approve"
    assert completed["result_payload"]["approved"] is True
