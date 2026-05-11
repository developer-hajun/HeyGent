from __future__ import annotations

from app.api.memory_observation import attach_memory_observation_to_task
from app.domain.tasks.models import TaskRun
from tests.fakes import InMemoryTaskRepository


def test_attach_memory_observation_to_task_persists_result_payload():
    repository = InMemoryTaskRepository()
    task = TaskRun(
        task_run_id="task_1",
        task_type="agent.loop",
        owner_key="1",
        session_key="session_1",
        status="COMPLETED",
        input_payload={
            "memory_context_meta": {
                "recall": {
                    "status": "injected",
                    "source": "backend",
                    "query_present": True,
                    "workspace_key_present": True,
                    "count": 1,
                    "memory_ids": [3],
                    "memory_types": ["FACT"],
                    "store_types": ["AGENT_MEMORY"],
                    "scope_types": ["GLOBAL"],
                    "failed": False,
                }
            }
        },
        result_payload={"text": "완료"},
    )
    repository.create_task(task)

    attach_memory_observation_to_task(
        task=task,
        repository=repository,
        writeback={
            "status": "succeeded",
            "attempted": True,
            "candidate_count": 1,
            "memory_types": ["PREFERENCE"],
            "store_types": ["USER_PROFILE"],
            "scope_types": ["GLOBAL"],
            "operation_types": ["ADD"],
            "failed": False,
        },
    )

    saved = repository.get_task("task_1")
    observation = saved.result_payload["memory_observation"]
    assert saved.result_payload["text"] == "완료"
    assert observation["recall"]["memory_ids"] == [3]
    assert observation["writeback"]["status"] == "succeeded"
    assert observation["mark_used"]["status"] == "skipped"
