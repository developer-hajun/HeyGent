from app.contracts.task.step_status import StepStatus
from app.contracts.task.task_status import TaskStatus
from app.domain.tasks.events import build_task_event
from app.domain.tasks.models import StepRun, TaskRun
from app.storage.sqlite import SQLiteTaskRepository


def test_sqlite_repository_persists_task_step_event_approval_and_provider_auth(tmp_path):
    repository = SQLiteTaskRepository(tmp_path / "repo.db")
    task = TaskRun(task_run_id="task_1", task_type="agent.loop", intent_type="agent.loop", entry_executor_key="agent.loop", owner_key="user", status=TaskStatus.PENDING, title="테스트 태스크")
    second_task = TaskRun(task_run_id="task_2", task_type="agent.loop", intent_type="agent.loop", entry_executor_key="agent.loop", owner_key="user", status=TaskStatus.COMPLETED, title="완료 태스크")
    step = StepRun(step_run_id="step_1", task_run_id="task_1", step_order=1, step_type="agent.loop.execute", executor_key="agent.loop", status=StepStatus.PENDING, title="테스트 스텝")

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
            "scope_text": "agent.loop,model.request",
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
    assert repository.get_task("task_1").entry_executor_key == "agent.loop"
    assert repository.count_tasks() == 2
    assert repository.count_tasks(status=TaskStatus.PENDING) == 1
    assert listed_tasks[0].status == TaskStatus.PENDING
    assert repository.list_steps("task_1")[0].step_run_id == "step_1"
    assert repository.list_steps("task_1")[0].title == "테스트 스텝"
    assert "agentDetail" in repository.list_steps("task_1")[0].detail_json
    with repository._connect() as connection:
        applied_migrations = {
            row["migration_id"] for row in connection.execute("SELECT migration_id FROM schema_migrations").fetchall()
        }
    assert "20260422_task_loop_anchors" in applied_migrations
    assert "20260422_provider_oauth_code_verifier" in applied_migrations
    with repository._connect() as connection:
        task_columns = {row["name"] for row in connection.execute("PRAGMA table_info(task_runs)").fetchall()}
    assert "entry_executor_key" in task_columns
    assert repository.list_events("task_1")[0].event_id == event.event_id
    assert repository.get_open_approval("task_1")["approval_id"] == approval["approval_id"]
    assert oauth_state["state"] == "state_123"
    assert token["access_token"] == "token-123"
    assert "agent.loop" in token["scopes"]
    assert consumed_state["status"] == "CONSUMED"
    assert deleted_token is True
    assert cleared_states >= 0
    assert repository.get_provider_token("openai_oauth") is None


def test_sqlite_repository_only_pending_approval_can_be_resolved_or_canceled(tmp_path):
    repository = SQLiteTaskRepository(tmp_path / "repo.db")
    task = TaskRun(
        task_run_id="task_pending_only",
        task_type="agent.loop",
        intent_type="agent.loop",
        entry_executor_key="agent.loop",
        owner_key="user",
        status=TaskStatus.WAITING,
        title="승인 대기 태스크",
    )
    step = StepRun(
        step_run_id="step_pending_only",
        task_run_id=task.task_run_id,
        step_order=1,
        step_type="agent.loop.execute",
        executor_key="agent.loop",
        status=StepStatus.WAITING,
        title="승인 대기 스텝",
    )
    repository.create_task(task)
    repository.create_step(step)

    resolved_approval = repository.create_approval_request(task.task_run_id, step.step_run_id, {"reason": "resolve once"})
    first_resolve = repository.resolve_approval_request(resolved_approval["approval_id"], {"approved": True})

    assert first_resolve is not None
    assert first_resolve["status"] == "RESOLVED"
    assert repository.resolve_approval_request(resolved_approval["approval_id"], {"approved": True}) is None
    assert repository.cancel_approval_request(resolved_approval["approval_id"]) is None

    canceled_approval = repository.create_approval_request(task.task_run_id, step.step_run_id, {"reason": "cancel once"})
    first_cancel = repository.cancel_approval_request(canceled_approval["approval_id"])

    assert first_cancel is not None
    assert first_cancel["status"] == "CANCELED"
    assert repository.resolve_approval_request(canceled_approval["approval_id"], {"approved": True}) is None
    assert repository.cancel_approval_request(canceled_approval["approval_id"]) is None
