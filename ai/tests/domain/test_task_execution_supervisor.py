import asyncio
from types import SimpleNamespace

import pytest

from app.domain.orchestration.contracts import OrchestrationRequest
from app.domain.orchestration.task_execution_supervisor import TaskExecutionSupervisor, TaskExecutionSupervisorConfig
from tests.fakes import InMemoryTaskRepository


@pytest.mark.asyncio
async def test_task_execution_supervisor_claims_and_executes_queued_task():
    repository = InMemoryTaskRepository()
    executed: list[str] = []
    completed: list[str] = []

    class FakeOrchestrator:
        async def enqueue_start(self, request: OrchestrationRequest):
            task = SimpleNamespace(
                task_run_id=request.task_run_id or "task-supervised",
                task_type="agent.loop",
                owner_key=request.owner_key,
                session_key=request.session_key,
                status="PENDING",
                input_payload=request.input_payload,
                result_payload={},
                todo_state={},
                wait_payload={},
                current_step_run_id=None,
                title="supervised",
                error_message=None,
                progress_summary=None,
                queue_status=None,
                claim_owner=None,
                queued_at=None,
                claimed_at=None,
                lease_expires_at=None,
                heartbeat_at=None,
                next_attempt_at=None,
                attempts=0,
                last_claim_error=None,
                revision=0,
                created_at=None,
                started_at=None,
                updated_at=None,
                ended_at=None,
            )
            return repository.create_pending_task(task)

        async def execute_claimed(self, task):
            executed.append(task.task_run_id)
            task.status = "COMPLETED"
            task.queue_status = "terminal"
            return repository.update_task(task)

    supervisor = TaskExecutionSupervisor(
        repository=repository,
        orchestrator=FakeOrchestrator(),
        config=TaskExecutionSupervisorConfig(worker_count=1, poll_interval_seconds=0.05),
        instance_id="test-supervisor",
    )
    await supervisor.start()
    try:
        await supervisor.submit(
            OrchestrationRequest(owner_key="42", session_key="session-1", input_payload={"prompt": "hi"}),
            on_complete=lambda task: _record_completion(completed, task.task_run_id),
        )
        for _ in range(20):
            if completed:
                break
            await asyncio.sleep(0.05)
    finally:
        await supervisor.stop()

    assert executed == ["task-supervised"]
    assert completed == ["task-supervised"]
    saved = repository.get_task("task-supervised")
    assert saved is not None
    assert saved.status == "COMPLETED"


async def _record_completion(target: list[str], task_run_id: str) -> None:
    target.append(task_run_id)


@pytest.mark.asyncio
async def test_task_execution_supervisor_does_not_fail_task_when_completion_callback_fails():
    repository = InMemoryTaskRepository()

    class FakeOrchestrator:
        async def enqueue_start(self, request: OrchestrationRequest):
            task = SimpleNamespace(
                task_run_id=request.task_run_id or "task-callback-fails",
                task_type="agent.loop",
                owner_key=request.owner_key,
                session_key=request.session_key,
                status="PENDING",
                input_payload=request.input_payload,
                result_payload={},
                todo_state={},
                wait_payload={},
                current_step_run_id=None,
                title="supervised",
                error_message=None,
                progress_summary=None,
                queue_status=None,
                claim_owner=None,
                queued_at=None,
                claimed_at=None,
                lease_expires_at=None,
                heartbeat_at=None,
                next_attempt_at=None,
                attempts=0,
                last_claim_error=None,
                revision=0,
                created_at=None,
                started_at=None,
                updated_at=None,
                ended_at=None,
            )
            return repository.create_pending_task(task)

        async def execute_claimed(self, task):
            task.status = "COMPLETED"
            task.queue_status = "terminal"
            return repository.update_task(task)

    supervisor = TaskExecutionSupervisor(
        repository=repository,
        orchestrator=FakeOrchestrator(),
        config=TaskExecutionSupervisorConfig(worker_count=1, poll_interval_seconds=0.05),
        instance_id="test-supervisor",
    )
    await supervisor.start()
    try:
        await supervisor.submit(
            OrchestrationRequest(owner_key="42", session_key="session-1", input_payload={"prompt": "hi"}),
            on_complete=_raise_completion_error,
        )
        for _ in range(20):
            saved = repository.get_task("task-callback-fails")
            if saved is not None and saved.status == "COMPLETED":
                break
            await asyncio.sleep(0.05)
    finally:
        await supervisor.stop()

    saved = repository.get_task("task-callback-fails")
    assert saved is not None
    assert saved.status == "COMPLETED"
    assert saved.queue_status == "terminal"
    assert saved.last_claim_error is None


async def _raise_completion_error(task) -> None:
    raise RuntimeError("websocket is already gone")
