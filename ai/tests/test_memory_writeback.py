from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.api.memory_writeback import writeback_persistent_memory_candidates
from app.clients.backend_memory import BackendMemoryClientError


class FakeMemoryClient:
    def __init__(self, *, fail: bool = False) -> None:
        self.calls = []
        self.fail = fail

    async def create_candidates(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise BackendMemoryClientError("backend failed")
        return []


class FakeExtractor:
    def __init__(self, candidates=None, *, fail: bool = False) -> None:
        self.calls = []
        self.candidates = candidates or []
        self.fail = fail

    async def extract_candidates(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise RuntimeError("extract failed")
        return list(self.candidates)


@pytest.mark.asyncio
async def test_writeback_extracts_and_posts_candidates_to_backend():
    candidate = {
        "memoryType": "PREFERENCE",
        "storeType": "USER_PROFILE",
        "scopeType": "GLOBAL",
        "operationType": "ADD",
        "content": "사용자는 짧은 답변을 선호한다.",
        "metadata": {"source": "ai.writeback"},
        "importance": 0.8,
        "confidence": 0.9,
    }
    memory_client = FakeMemoryClient()
    extractor = FakeExtractor([candidate])
    app_state = SimpleNamespace(backend_memory_client=memory_client, memory_extractor=extractor)

    await writeback_persistent_memory_candidates(
        app_state=app_state,
        user_id="1",
        user_message="앞으로 짧게 답해줘.",
        assistant_message="알겠습니다.",
        session_id="session_1",
        workspace_key="workspace-a",
        task_run_id="task_1",
        user_message_id="msg_1",
        assistant_message_id="msg_2",
    )

    assert len(extractor.calls) == 1
    assert extractor.calls[0]["context"].workspace_key == "workspace-a"
    assert memory_client.calls == [{"user_id": "1", "candidates": [candidate]}]


@pytest.mark.asyncio
async def test_writeback_is_nonfatal_when_extractor_fails():
    memory_client = FakeMemoryClient()
    extractor = FakeExtractor(fail=True)
    app_state = SimpleNamespace(backend_memory_client=memory_client, memory_extractor=extractor)

    await writeback_persistent_memory_candidates(
        app_state=app_state,
        user_id="1",
        user_message="기억해줘.",
        assistant_message="알겠습니다.",
        session_id="session_1",
    )

    assert memory_client.calls == []


@pytest.mark.asyncio
async def test_writeback_is_nonfatal_when_backend_fails():
    memory_client = FakeMemoryClient(fail=True)
    extractor = FakeExtractor(
        [
            {
                "memoryType": "FACT",
                "storeType": "AGENT_MEMORY",
                "scopeType": "GLOBAL",
                "operationType": "ADD",
                "content": "사용자는 테스트를 사용한다.",
                "metadata": {"source": "ai.writeback"},
                "importance": 0.7,
                "confidence": 0.9,
            }
        ]
    )
    app_state = SimpleNamespace(backend_memory_client=memory_client, memory_extractor=extractor)

    await writeback_persistent_memory_candidates(
        app_state=app_state,
        user_id="1",
        user_message="기억해줘.",
        assistant_message="알겠습니다.",
        session_id="session_1",
    )

    assert len(memory_client.calls) == 1
