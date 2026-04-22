from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus
from app.domain.tasks.events import build_task_event
from app.domain.tasks.models import StepRun, TaskRun
from app.storage.sqlite import SQLiteTaskRepository


def test_sqlite_repository_persists_task_step_event_approval_and_provider_auth(tmp_path):
    repository = SQLiteTaskRepository(tmp_path / "repo.db")
    task = TaskRun(task_run_id="task_1", task_type="stub", intent_type="stub.echo", entry_capability="stub.echo", owner_key="user", status=TaskStatus.PENDING, title="테스트 태스크")
    second_task = TaskRun(task_run_id="task_2", task_type="stub", intent_type="stub.echo", entry_capability="stub.echo", owner_key="user", status=TaskStatus.COMPLETED, title="완료 태스크")
    step = StepRun(step_run_id="step_1", task_run_id="task_1", step_order=1, step_type="echo", executor_key="stub.echo", status=StepStatus.PENDING, title="테스트 스텝")

    repository.create_task(task)
    repository.create_task(second_task)
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
    listed_tasks = repository.list_tasks(limit=10, offset=0)

    assert repository.get_task("task_1") is not None
    assert repository.get_task("task_1").title == "테스트 태스크"
    assert repository.count_tasks() == 2
    assert repository.count_tasks(status=TaskStatus.PENDING) == 1
    assert listed_tasks[0].task_run_id == "task_1"
    assert repository.list_steps("task_1")[0].step_run_id == "step_1"
    assert repository.list_steps("task_1")[0].title == "테스트 스텝"
    assert "agentDetail" in repository.list_steps("task_1")[0].detail_json
    assert repository.list_events("task_1")[0].event_id == event.event_id
    assert repository.get_open_approval("task_1")["approval_id"] == approval["approval_id"]
    assert oauth_state["state"] == "state_123"
    assert token["access_token"] == "token-123"
    assert "model.generate" in token["scopes"]
    assert consumed_state["status"] == "CONSUMED"
    assert deleted_token is True
    assert cleared_states >= 0
    assert repository.get_provider_token("openai_oauth") is None
