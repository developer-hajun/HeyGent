from __future__ import annotations

import pytest

from app.domain.orchestration.agent.memory.memory_extractor import LlmMemoryExtractor, MemoryExtractionContext


class FakeStructuredProvider:
    def __init__(self, payload, *, fail: bool = False):
        self.payload = payload
        self.fail = fail
        self.calls = []

    async def extract_memory_json(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise RuntimeError("provider failed")
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
            "metadata": {"source": "ai.writeback", "category": "preference", "sensitivity": "low", "ttl": "long", "tags": ["style"]},
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
async def test_memory_extractor_normalizes_llm_profile_candidate_without_explicit_remember_request():
    provider = FakeStructuredProvider(
        {
            "candidates": [
                {
                    "memoryType": "profile",
                    "scopeType": "global",
                    "content": "사용자의 이름은 김상지이다.",
                    "summary": "사용자 이름",
                    "metadata": {"category": "profile", "tags": ["name"]},
                    "importance": 0.9,
                    "confidence": 0.95,
                    "evidence": "내 이름은 김상지야",
                }
            ]
        }
    )
    extractor = LlmMemoryExtractor(provider=provider)

    candidates = await extractor.extract_candidates(
        user_message="내 이름은 김상지야",
        assistant_message="알겠습니다. 앞으로 김상지님이라고 불러드릴까요?",
        context=MemoryExtractionContext(user_id="1", session_id="session_1", task_run_id="task_1", assistant_message_id="msg_2"),
    )

    assert candidates == [
        {
            "memoryType": "PROFILE",
            "storeType": "USER_PROFILE",
            "scopeType": "GLOBAL",
            "operationType": "ADD",
            "content": "사용자의 이름은 김상지이다.",
            "metadata": {"source": "ai.writeback", "category": "profile", "sensitivity": "low", "ttl": "long", "tags": ["name"]},
            "importance": 0.9,
            "confidence": 0.95,
            "summary": "사용자 이름",
            "evidence": "내 이름은 김상지야",
            "sourceTaskRunId": "task_1",
            "sourceMessageId": "msg_2",
        }
    ]


@pytest.mark.asyncio
async def test_memory_extractor_normalizes_llm_preference_candidate_without_explicit_remember_request():
    provider = FakeStructuredProvider(
        {
            "candidates": [
                {
                    "memoryType": "preference",
                    "scopeType": "global",
                    "content": "사용자는 국수를 좋아한다.",
                    "summary": "국수 선호",
                    "metadata": {"category": "preference", "tags": ["food"]},
                    "importance": 0.8,
                    "confidence": 0.9,
                    "evidence": "나 국수 좋아해",
                }
            ]
        }
    )
    extractor = LlmMemoryExtractor(provider=provider)

    candidates = await extractor.extract_candidates(
        user_message="나 국수 좋아해",
        assistant_message="국수도 좋죠.",
        context=MemoryExtractionContext(user_id="1", session_id="session_1"),
    )

    assert candidates[0]["memoryType"] == "PREFERENCE"
    assert candidates[0]["storeType"] == "USER_PROFILE"
    assert candidates[0]["scopeType"] == "GLOBAL"
    assert candidates[0]["content"] == "사용자는 국수를 좋아한다."
    assert candidates[0]["metadata"]["category"] == "preference"


@pytest.mark.asyncio
async def test_memory_extractor_reraises_provider_failure_without_rule_fallback_storage():
    provider = FakeStructuredProvider({"candidates": []}, fail=True)
    extractor = LlmMemoryExtractor(provider=provider)

    with pytest.raises(RuntimeError, match="provider failed"):
        await extractor.extract_candidates(
            user_message="나 국수 좋아해",
            assistant_message="답변입니다.",
            context=MemoryExtractionContext(user_id="1", session_id="session_1"),
        )


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
    assert with_workspace[0]["metadata"]["category"] == "instruction"


@pytest.mark.asyncio
async def test_memory_extractor_preserves_event_reason_task_state_categories():
    provider = FakeStructuredProvider(
        {
            "candidates": [
                {
                    "memoryType": "FACT",
                    "scopeType": "WORKSPACE",
                    "content": "장기기억 구현은 operation reconciliation 이후 candidate 분류 작업이 남아 있다.",
                    "summary": "장기기억 구현 task state",
                    "metadata": {"category": "task-state", "tags": ["memory", "implementation"]},
                    "importance": 0.8,
                    "confidence": 0.9,
                },
                {
                    "memoryType": "FACT",
                    "scopeType": "GLOBAL",
                    "content": "사용자가 Jira 형식 변경을 요청한 이유는 발표와 협업 정리를 쉽게 하기 위해서다.",
                    "summary": "Jira 형식 변경 이유",
                    "category": "reason",
                    "importance": 0.7,
                    "confidence": 0.85,
                },
                {
                    "memoryType": "FACT",
                    "scopeType": "WORKSPACE",
                    "content": "IoT 3D 모델링은 1차 초안 후 부품 테스트를 거쳐 고도화하기로 했다.",
                    "summary": "IoT 모델링 진행 이벤트",
                    "memoryCategory": "event",
                    "importance": 0.75,
                    "confidence": 0.9,
                },
            ]
        }
    )
    extractor = LlmMemoryExtractor(provider=provider)

    candidates = await extractor.extract_candidates(
        user_message="장기기억 작업 상태와 Jira 이유, IoT 진행 이벤트를 기억해줘.",
        assistant_message="정리했습니다.",
        context=MemoryExtractionContext(user_id="1", session_id="session_1", workspace_key="workspace-a"),
    )

    assert [candidate["metadata"]["category"] for candidate in candidates] == ["task_state", "reason", "event"]
    assert candidates[0]["metadata"]["tags"] == ["memory", "implementation"]
    assert candidates[0]["metadata"]["workspaceKey"] == "workspace-a"
    assert candidates[2]["metadata"]["workspaceKey"] == "workspace-a"


@pytest.mark.asyncio
async def test_memory_extractor_normalizes_sensitivity_ttl_and_validity_metadata():
    provider = FakeStructuredProvider(
        {
            "candidates": [
                {
                    "memoryType": "FACT",
                    "scopeType": "WORKSPACE",
                    "content": "IoT 모델링 초안은 2026년 5월 20일까지 유효한 1차 시연 기준이다.",
                    "summary": "IoT 모델링 1차 시연 기준",
                    "validFrom": "2026-05-11",
                    "validUntil": "2026-05-20T18:00:00+09:00",
                    "expiresAt": "2026-06-01T00:00:00",
                    "metadata": {
                        "category": "event",
                        "sensitivity": "MEDIUM",
                        "ttl": "short",
                        "sourceTimestamp": "2026-05-11T10:30:00+09:00",
                        "eventTime": "2026-05-20T15:00:00",
                        "reason": "발표 시연 기준을 명확히 하기 위해 저장한다.",
                    },
                    "importance": 0.8,
                    "confidence": 0.9,
                }
            ]
        }
    )
    extractor = LlmMemoryExtractor(provider=provider)

    candidates = await extractor.extract_candidates(
        user_message="IoT 모델링 초안 시연 기준을 기억해줘.",
        assistant_message="정리했습니다.",
        context=MemoryExtractionContext(user_id="1", session_id="session_1", workspace_key="workspace-a"),
    )

    candidate = candidates[0]
    assert candidate["validFrom"] == "2026-05-11T00:00:00"
    assert candidate["validUntil"] == "2026-05-20T18:00:00"
    assert candidate["expiresAt"] == "2026-06-01T00:00:00"
    assert candidate["metadata"] == {
        "source": "ai.writeback",
        "category": "event",
        "sensitivity": "medium",
        "ttl": "short",
        "workspaceKey": "workspace-a",
        "sourceTimestamp": "2026-05-11T10:30:00",
        "eventTime": "2026-05-20T15:00:00",
        "reason": "발표 시연 기준을 명확히 하기 위해 저장한다.",
    }


@pytest.mark.asyncio
async def test_memory_extractor_ignores_invalid_validity_metadata_and_defaults_ttl():
    provider = FakeStructuredProvider(
        {
            "candidates": [
                {
                    "memoryType": "FACT",
                    "scopeType": "GLOBAL",
                    "content": "장기기억 구현 task state는 metadata 고도화 단계다.",
                    "metadata": {
                        "category": "task_state",
                        "sensitivity": "unknown",
                        "ttl": "forever",
                        "sourceTimestamp": "어제",
                    },
                    "validFrom": "다음 주",
                    "importance": 0.8,
                    "confidence": 0.9,
                }
            ]
        }
    )
    extractor = LlmMemoryExtractor(provider=provider)

    candidates = await extractor.extract_candidates(
        user_message="장기기억 구현 상태를 기억해줘.",
        assistant_message="정리했습니다.",
        context=MemoryExtractionContext(user_id="1", session_id="session_1"),
    )

    candidate = candidates[0]
    assert "validFrom" not in candidate
    assert "sourceTimestamp" not in candidate["metadata"]
    assert candidate["metadata"]["sensitivity"] == "low"
    assert candidate["metadata"]["ttl"] == "medium"


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
