from __future__ import annotations

import pytest

from app.domain.orchestration.agent.memory.memory_extractor import LlmMemoryExtractor, MemoryExtractionContext


class FakeStructuredProvider:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    async def extract_memory_json(self, **kwargs):
        self.calls.append(kwargs)
        return self.payload


@pytest.mark.asyncio
async def test_memory_extractor_normalizes_preference_candidate_for_backend_contract():
    provider = FakeStructuredProvider(
        {
            "candidates": [
                {
                    "memoryType": "preference",
                    "scopeType": "global",
                    "content": "사용자는 답변을 짧게 받는 것을 선호한다.",
                    "summary": "짧은 답변 선호",
                    "metadata": {"tags": ["style"]},
                    "importance": 0.8,
                    "confidence": 0.9,
                    "evidence": "짧게 답해줘.",
                }
            ]
        }
    )
    extractor = LlmMemoryExtractor(provider=provider)

    candidates = await extractor.extract_candidates(
        user_message="앞으로는 짧게 답해줘.",
        assistant_message="알겠습니다.",
        context=MemoryExtractionContext(user_id="1", session_id="session_1", task_run_id="task_1", assistant_message_id="msg_2"),
    )

    assert candidates == [
        {
            "memoryType": "PREFERENCE",
            "storeType": "USER_PROFILE",
            "scopeType": "GLOBAL",
            "operationType": "ADD",
            "content": "사용자는 답변을 짧게 받는 것을 선호한다.",
            "metadata": {"source": "ai.writeback", "tags": ["style"]},
            "importance": 0.8,
            "confidence": 0.9,
            "summary": "짧은 답변 선호",
            "evidence": "짧게 답해줘.",
            "sourceTaskRunId": "task_1",
            "sourceMessageId": "msg_2",
        }
    ]


@pytest.mark.asyncio
async def test_memory_extractor_drops_low_score_candidates():
    provider = FakeStructuredProvider(
        {
            "candidates": [
                {
                    "memoryType": "FACT",
                    "scopeType": "GLOBAL",
                    "content": "불확실한 사실",
                    "importance": 0.8,
                    "confidence": 0.6,
                }
            ]
        }
    )
    extractor = LlmMemoryExtractor(provider=provider)

    candidates = await extractor.extract_candidates(
        user_message="아마 그럴 수도 있어.",
        assistant_message="확인했습니다.",
        context=MemoryExtractionContext(user_id="1", session_id="session_1"),
    )

    assert candidates == []


@pytest.mark.asyncio
async def test_memory_extractor_requires_workspace_key_for_workspace_scope():
    provider = FakeStructuredProvider(
        {
            "candidates": [
                {
                    "memoryType": "INSTRUCTION",
                    "scopeType": "WORKSPACE",
                    "content": "이 프로젝트에서는 PR 요약을 한국어로 작성한다.",
                    "importance": 0.7,
                    "confidence": 0.9,
                }
            ]
        }
    )
    extractor = LlmMemoryExtractor(provider=provider)

    without_workspace = await extractor.extract_candidates(
        user_message="이 프로젝트에서는 PR 요약을 한국어로 작성해.",
        assistant_message="알겠습니다.",
        context=MemoryExtractionContext(user_id="1", session_id="session_1"),
    )
    with_workspace = await extractor.extract_candidates(
        user_message="이 프로젝트에서는 PR 요약을 한국어로 작성해.",
        assistant_message="알겠습니다.",
        context=MemoryExtractionContext(user_id="1", session_id="session_1", workspace_key="workspace-a"),
    )

    assert without_workspace == []
    assert with_workspace[0]["storeType"] == "AGENT_MEMORY"
    assert with_workspace[0]["metadata"]["workspaceKey"] == "workspace-a"


@pytest.mark.asyncio
async def test_memory_extractor_does_not_call_llm_when_user_denies_storage():
    provider = FakeStructuredProvider({"candidates": [{"memoryType": "FACT", "content": "x", "importance": 1, "confidence": 1}]})
    extractor = LlmMemoryExtractor(provider=provider)

    candidates = await extractor.extract_candidates(
        user_message="이 내용은 저장하지 마.",
        assistant_message="알겠습니다.",
        context=MemoryExtractionContext(user_id="1", session_id="session_1"),
    )

    assert candidates == []
    assert provider.calls == []


@pytest.mark.asyncio
async def test_memory_extractor_allows_security_policy_without_secret_value():
    provider = FakeStructuredProvider(
        {
            "candidates": [
                {
                    "memoryType": "INSTRUCTION",
                    "scopeType": "GLOBAL",
                    "content": "이 프로젝트에서는 access token을 task input에 넣지 않는다.",
                    "importance": 0.8,
                    "confidence": 0.9,
                }
            ]
        }
    )
    extractor = LlmMemoryExtractor(provider=provider)

    candidates = await extractor.extract_candidates(
        user_message="앞으로 access token은 task input에 넣지 않는 걸 기억해줘.",
        assistant_message="알겠습니다.",
        context=MemoryExtractionContext(user_id="1", session_id="session_1"),
    )

    assert candidates[0]["content"] == "이 프로젝트에서는 access token을 task input에 넣지 않는다."


@pytest.mark.asyncio
async def test_memory_extractor_drops_secret_value_candidates():
    provider = FakeStructuredProvider(
        {
            "candidates": [
                {
                    "memoryType": "FACT",
                    "scopeType": "GLOBAL",
                    "content": "사용자의 access_token=abcdef1234567890",
                    "importance": 0.8,
                    "confidence": 0.9,
                }
            ]
        }
    )
    extractor = LlmMemoryExtractor(provider=provider)

    candidates = await extractor.extract_candidates(
        user_message="기억해줘.",
        assistant_message="알겠습니다.",
        context=MemoryExtractionContext(user_id="1", session_id="session_1"),
    )

    assert candidates == []
