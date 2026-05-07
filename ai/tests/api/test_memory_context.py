from types import SimpleNamespace

import pytest

from app.api.memory_context import attach_persistent_memory_context, select_memory_recall_query
from app.clients.backend_memory import BackendMemoryClientError, BackendMemoryItem


class FakeMemoryClient:
    def __init__(self, memories=None, *, fail: bool = False) -> None:
        self.memories = list(memories or [])
        self.fail = fail
        self.calls = []

    async def recall(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise BackendMemoryClientError("recall failed")
        return list(self.memories)


def _memory(content: str) -> BackendMemoryItem:
    return BackendMemoryItem(
        id=1,
        memory_type="PREFERENCE",
        store_type="PROFILE",
        scope_type="GLOBAL",
        content=content,
        summary="선호 요약",
        importance=0.8,
        confidence=0.9,
        metadata={"workspaceKey": "team-a", "token": "hidden"},
    )


def test_select_memory_recall_query_uses_prompt_like_fields():
    assert select_memory_recall_query({"prompt": "  현재 요청  "}) == "현재 요청"
    assert select_memory_recall_query({"count": 1, "message": ""}) is None
    assert select_memory_recall_query({"subject": "회의 정리"}) == "회의 정리"


@pytest.mark.asyncio
async def test_attach_persistent_memory_context_replaces_client_supplied_context():
    memory_client = FakeMemoryClient([_memory("사용자는 회의 요약을 짧게 받는 것을 선호한다.")])
    task_input = {
        "prompt": "오늘 회의 정리해줘",
        "persistent_memory_context": "client supplied context",
        "memory_context": "legacy client supplied context",
        "memory_context_meta": {"recall": {"status": "client_supplied"}},
    }

    await attach_persistent_memory_context(
        app_state=SimpleNamespace(backend_memory_client=memory_client),
        task_input=task_input,
        user_id="7",
        query="오늘 회의 정리해줘",
        workspace_key="team-a",
    )

    assert memory_client.calls == [
        {
            "user_id": "7",
            "query": "오늘 회의 정리해줘",
            "limit": 5,
            "workspace_key": "team-a",
        }
    ]
    assert "client supplied context" not in task_input["persistent_memory_context"]
    assert "legacy client supplied context" not in str(task_input)
    assert "사용자는 회의 요약을 짧게 받는 것을 선호한다." in task_input["persistent_memory_context"]
    assert "hidden" not in task_input["persistent_memory_context"]
    assert task_input["memory_context_meta"]["recall"] == {
        "status": "injected",
        "source": "backend",
        "query_present": True,
        "workspace_key_present": True,
        "count": 1,
        "memory_ids": [1],
        "memory_types": ["PREFERENCE"],
        "store_types": ["PROFILE"],
        "scope_types": ["GLOBAL"],
        "failed": False,
    }


@pytest.mark.asyncio
async def test_attach_persistent_memory_context_is_nonfatal_on_backend_failure():
    task_input = {"prompt": "실패해도 계속 진행", "persistent_memory_context": "client supplied context"}

    await attach_persistent_memory_context(
        app_state=SimpleNamespace(backend_memory_client=FakeMemoryClient(fail=True)),
        task_input=task_input,
        user_id="7",
        query="실패해도 계속 진행",
    )

    assert "persistent_memory_context" not in task_input
    assert task_input["memory_context_meta"]["recall"]["status"] == "failed"
    assert task_input["memory_context_meta"]["recall"]["failed"] is True
    assert task_input["memory_context_meta"]["recall"]["reason"] == "backend_memory_client_error"


@pytest.mark.asyncio
async def test_attach_persistent_memory_context_records_empty_recall():
    task_input = {"prompt": "새 요청"}

    await attach_persistent_memory_context(
        app_state=SimpleNamespace(backend_memory_client=FakeMemoryClient([])),
        task_input=task_input,
        user_id="7",
        query="새 요청",
    )

    assert "persistent_memory_context" not in task_input
    assert task_input["memory_context_meta"]["recall"]["status"] == "empty"
    assert task_input["memory_context_meta"]["recall"]["count"] == 0
