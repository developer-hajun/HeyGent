from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus
from app.domain.tasks.events import build_task_event
from app.domain.tasks.models import StepRun, TaskRun
from app.storage.sqlite import SQLiteTaskRepository


def test_sqlite_repository_persists_task_step_event_approval_and_provider_auth(tmp_path):
    repository = SQLiteTaskRepository(tmp_path / "repo.db")
    task = TaskRun(task_run_id="task_1", task_type="stub", flow_name="echo_flow", owner_key="user", status=TaskStatus.PENDING)
    step = StepRun(step_run_id="step_1", task_run_id="task_1", step_order=1, step_type="echo", status=StepStatus.PENDING)

    repository.create_task(task)
    repository.create_step(step)
    event = repository.append_event(build_task_event(event_type="task.created", task_run_id="task_1", producer="test"))
    approval = repository.create_approval_request("task_1", "step_1", {"reason": "approve"})
    oauth_state = repository.create_provider_oauth_state("openai_oauth", "state_123", "http://localhost/callback")
    repository.upsert_provider_token(
        "openai_oauth",
        {
            "access_token": "token-123",
            "refresh_token": "refresh-123",
            "token_type": "Bearer",
            "scope_text": "model.generate,model.request",
            "expires_at": None,
            "raw_payload": {"ok": True},
        },
    )
    token = repository.get_provider_token("openai_oauth")
    consumed_state = repository.consume_provider_oauth_state("openai_oauth", "state_123")
    deleted_token = repository.delete_provider_token("openai_oauth")
    cleared_states = repository.delete_provider_oauth_states("openai_oauth")

    assert repository.get_task("task_1") is not None
    assert repository.list_steps("task_1")[0].step_run_id == "step_1"
    assert repository.list_events("task_1")[0].event_id == event.event_id
    assert repository.get_open_approval("task_1")["approval_id"] == approval["approval_id"]
    assert oauth_state["state"] == "state_123"
    assert token["access_token"] == "token-123"
    assert "model.generate" in token["scopes"]
    assert consumed_state["status"] == "CONSUMED"
    assert deleted_token is True
    assert cleared_states >= 0
    assert repository.get_provider_token("openai_oauth") is None
