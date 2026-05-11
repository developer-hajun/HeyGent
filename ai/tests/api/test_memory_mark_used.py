from types import SimpleNamespace

import pytest

from app.api.memory_mark_used import mark_used_recalled_memories
from app.clients.backend_memory import BackendMemoryClientError


class FakeMemoryClient:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls = []

    async def mark_used(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise BackendMemoryClientError("mark used failed")
        return SimpleNamespace(id=kwargs["memory_id"])


def _task_input(memory_ids=None) -> dict:
    memory_ids = memory_ids or [10, 10, 11]
    return {
        "persistent_memory_context": """
<memory-context>
아래 내용은 이전에 저장된 장기기억입니다.

- id: 10
  type: PREFERENCE
  store: USER_PROFILE
  scope: GLOBAL
  summary: MR 작성 형식 선호
  content: 사용자는 MR 작업내용을 짧게 정리하는 것을 선호한다.
- id: 11
  type: FACT
  store: AGENT_MEMORY
  scope: WORKSPACE
  summary: IoT 모델링 진행 상태
  content: IoT 3D 모델링은 1차 초안 단계이다.
</memory-context>
""".strip(),
        "memory_context_meta": {
            "recall": {
                "status": "injected",
                "memory_ids": memory_ids,
            }
        },
    }


@pytest.mark.asyncio
async def test_mark_used_recalled_memories_marks_attributed_memory_once():
    memory_client = FakeMemoryClient()

    observation = await mark_used_recalled_memories(
        app_state=SimpleNamespace(backend_memory_client=memory_client),
        task_input=_task_input(),
        user_id="7",
        assistant_message="MR 작업내용은 짧게 정리했습니다.",
        task_run_id="task_1",
    )

    assert memory_client.calls == [
        {
            "user_id": "7",
            "memory_id": 10,
            "usefulness_score": 0.7,
        }
    ]
    assert observation["status"] == "completed"
    assert observation["attempted"] is True
    assert observation["recalled_memory_ids"] == [10, 11]
    assert observation["used_memory_ids"] == [10]
    assert observation["skipped_memory_ids"] == [11]
    assert observation["scores"] == {"10": 0.7}
    assert observation["deduplicated"] is True
    assert observation["task_run_id_present"] is True


@pytest.mark.asyncio
async def test_mark_used_recalled_memories_skips_without_attribution():
    memory_client = FakeMemoryClient()

    observation = await mark_used_recalled_memories(
        app_state=SimpleNamespace(backend_memory_client=memory_client),
        task_input=_task_input(memory_ids=[10]),
        user_id="7",
        assistant_message="새로운 테스트 결과를 정리했습니다.",
        task_run_id="task_1",
    )

    assert memory_client.calls == []
    assert observation["status"] == "skipped"
    assert observation["reason"] == "no_memory_attribution"
    assert observation["used_memory_ids"] == []
    assert observation["skipped_memory_ids"] == [10]


@pytest.mark.asyncio
async def test_mark_used_recalled_memories_is_nonfatal_on_backend_failure():
    memory_client = FakeMemoryClient(fail=True)

    observation = await mark_used_recalled_memories(
        app_state=SimpleNamespace(backend_memory_client=memory_client),
        task_input=_task_input(memory_ids=[10]),
        user_id="7",
        assistant_message="MR 작업내용은 짧게 정리했습니다.",
        task_run_id="task_1",
    )

    assert len(memory_client.calls) == 1
    assert observation["status"] == "failed"
    assert observation["failed"] is True
    assert observation["failed_memory_ids"] == [10]
    assert observation["used_memory_ids"] == []


@pytest.mark.asyncio
async def test_mark_used_recalled_memories_skips_without_memory_client():
    observation = await mark_used_recalled_memories(
        app_state=SimpleNamespace(),
        task_input=_task_input(memory_ids=[10]),
        user_id="7",
        assistant_message="MR 작업내용은 짧게 정리했습니다.",
        task_run_id="task_1",
    )

    assert observation["status"] == "skipped"
    assert observation["reason"] == "memory_client_unavailable"
