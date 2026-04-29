from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.contracts.task.task_status import TaskStatus
from app.domain.orchestration.delegation.delegate_runtime import DelegateRuntime
from app.domain.orchestration.delegation.spec import ChildSessionLaunchResult


class FakeChildSessionLauncher:
    def __init__(self, result: ChildSessionLaunchResult | Exception) -> None:
        self.result = result
        self.launched: list[dict] = []

    def build_pending_detail(self, spec):
        return {"agentDetail": {"status": "PENDING", "agentId": f"{spec.parent_step_run_id}:agent.loop"}}

    def build_failed_detail(self, spec, error_message: str):
        return {"agentDetail": {"status": "FAILED", "summary": error_message}}

    def build_result_detail(self, spec, result):
        return {
            "agentDetail": {
                "status": result.status,
                "summary": result.summary,
                "childTaskRunId": result.child_task_run_id,
                "agentId": result.agent_id,
            }
        }

    async def launch(self, **kwargs):
        self.launched.append(kwargs)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakeHandoffRepository:
    def __init__(self) -> None:
        self.steps: list[object] = []
        self.created_handoffs: list[dict] = []
        self.completed_handoffs: list[tuple[str, dict]] = []

    def update_step(self, step):
        self.steps.append(step)
        return step

    def create_worker_handoff(self, payload):
        self.created_handoffs.append(payload)
        return payload

    def complete_worker_handoff(self, handoff_id, payload):
        self.completed_handoffs.append((handoff_id, payload))
        return {"handoff_id": handoff_id, **payload}


@pytest.mark.asyncio
async def test_delegate_runtime_records_worker_handoff_when_repository_supports_it():
    launcher = FakeChildSessionLauncher(
        ChildSessionLaunchResult(
            agent_id="agent_worker",
            child_task_run_id="task_child",
            status=TaskStatus.COMPLETED,
            summary="작업 완료",
        )
    )
    runtime = DelegateRuntime(launcher)
    repository = FakeHandoffRepository()
    task = SimpleNamespace(task_run_id="task_parent", owner_key="user_1", session_key="session_1")
    step = SimpleNamespace(step_run_id="step_parent", detail_json={})

    outcome = {
        "child_session": {
            "intent_type": "agent.loop",
            "entry_executor_key": "agent.loop",
            "input_payload": {"prompt": "하위 작업"},
            "metadata": {"profile_key": "worker.default"},
        }
    }

    result = await runtime.apply(task=task, step=step, outcome=outcome, repository=repository)

    assert repository.created_handoffs[0]["task_run_id"] == "task_parent"
    assert repository.created_handoffs[0]["parent_step_run_id"] == "step_parent"
    assert repository.created_handoffs[0]["worker_profile_id"] == "worker.default"
    assert repository.created_handoffs[0]["input_payload"]["child_intent_type"] == "agent.loop"
    completed_id, completed_payload = repository.completed_handoffs[0]
    assert completed_id == repository.created_handoffs[0]["handoff_id"]
    assert completed_payload["status"] == "COMPLETED"
    assert completed_payload["result_summary"]["childTaskRunId"] == "task_child"
    assert result["result_payload"]["childTaskRunId"] == "task_child"


@pytest.mark.asyncio
async def test_delegate_runtime_completes_handoff_as_failed_when_launch_fails():
    launcher = FakeChildSessionLauncher(RuntimeError("launch unavailable"))
    runtime = DelegateRuntime(launcher)
    repository = FakeHandoffRepository()
    task = SimpleNamespace(task_run_id="task_parent", owner_key="user_1", session_key=None)
    step = SimpleNamespace(step_run_id="step_parent", detail_json={})

    result = await runtime.apply(
        task=task,
        step=step,
        outcome={
            "child_session": {
                "intent_type": "agent.loop",
                "entry_executor_key": "agent.loop",
                "input_payload": {"prompt": "하위 작업"},
            }
        },
        repository=repository,
    )

    assert result["task_status"] == TaskStatus.FAILED
    assert repository.completed_handoffs[0][1]["status"] == "FAILED"
    assert "launch unavailable" in repository.completed_handoffs[0][1]["result_summary"]["error"]
