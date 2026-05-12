import asyncio
from types import SimpleNamespace

import pytest

from app.api.memory_context import (
    LlmMemoryRecallPlanner,
    attach_persistent_memory_context,
    plan_memory_recall,
    select_memory_recall_query,
)
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


class EmptyThenMemoryClient(FakeMemoryClient):
    async def recall(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            return []
        return list(self.memories)


class FakeRecallPlannerProvider:
    def __init__(self, payload=None, *, fail: bool = False, delay_seconds: float = 0.0) -> None:
        self.payload = payload or {}
        self.fail = fail
        self.delay_seconds = delay_seconds
        self.calls = []

    async def plan_memory_recall_json(self, **kwargs):
        self.calls.append(kwargs)
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        if self.fail:
            raise RuntimeError("planner failed")
        return self.payload


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


def test_plan_memory_recall_skips_low_value_greeting():
    plan = plan_memory_recall("안녕")

    assert plan.should_recall is False
    assert plan.reason == "low_value_query"


def test_plan_memory_recall_selects_user_preference_filters():
    plan = plan_memory_recall("앞으로 답변은 짧게 해줘", workspace_key="team-a")

    assert plan.should_recall is True
    assert plan.reason == "user_preference_needed"
    assert plan.filters() == {
        "store_type": "USER_PROFILE",
        "memory_type": "PREFERENCE",
        "scope_type": "GLOBAL",
        "metadata_categories": ["preference"],
    }


def test_plan_memory_recall_selects_workspace_task_state_filters():
    plan = plan_memory_recall("4번 장기기억 작업 이어서 해줘", workspace_key="team-a")

    assert plan.should_recall is True
    assert plan.reason == "workspace_memory_needed"
    assert plan.filters() == {
        "store_type": "AGENT_MEMORY",
        "memory_type": "FACT",
        "scope_type": "WORKSPACE",
        "workspace_key": "team-a",
        "metadata_categories": ["task_state", "fact"],
    }


@pytest.mark.asyncio
async def test_llm_memory_recall_planner_uses_model_structured_filters():
    provider = FakeRecallPlannerProvider(
        {
            "shouldRecall": True,
            "query": "MR 작성 선호",
            "reason": "사용자 MR 작성 형식 선호가 필요함",
            "limit": 3,
            "filters": {
                "storeType": "USER_PROFILE",
                "memoryType": "PREFERENCE",
                "scopeType": "GLOBAL",
                "metadataCategories": ["preference", "unknown"],
            },
        }
    )
    planner = LlmMemoryRecallPlanner(provider=provider)

    plan = await planner.plan_recall("MR 작업내용 정리해줘", workspace_key="team-a", limit=5)

    assert plan.should_recall is True
    assert plan.query == "MR 작성 선호"
    assert plan.reason == "사용자 MR 작성 형식 선호가 필요함"
    assert plan.limit == 3
    assert plan.planner_source == "llm"
    assert plan.planner_latency_ms is not None
    assert plan.filters() == {
        "store_type": "USER_PROFILE",
        "memory_type": "PREFERENCE",
        "scope_type": "GLOBAL",
        "metadata_categories": ["preference"],
    }
    assert provider.calls[0]["rule_plan"].should_recall is True


@pytest.mark.asyncio
async def test_llm_memory_recall_planner_handles_personalized_recommendation():
    provider = FakeRecallPlannerProvider(
        {
            "shouldRecall": True,
            "query": "사용자 점심 메뉴 선호",
            "reason": "점심 추천은 사용자 음식 선호가 필요함",
            "filters": {
                "storeType": "USER_PROFILE",
                "memoryType": "PREFERENCE",
                "scopeType": "GLOBAL",
                "metadataCategories": ["preference"],
            },
        }
    )
    planner = LlmMemoryRecallPlanner(provider=provider)

    plan = await planner.plan_recall("오늘 점심 뭐 먹을까?", workspace_key="team-a")

    assert plan.should_recall is True
    assert plan.query == "사용자 점심 메뉴 선호"
    assert plan.reason == "점심 추천은 사용자 음식 선호가 필요함"
    assert plan.planner_source == "llm"
    assert plan.filters() == {
        "store_type": "USER_PROFILE",
        "memory_type": "PREFERENCE",
        "scope_type": "GLOBAL",
        "metadata_categories": ["preference"],
    }


@pytest.mark.asyncio
async def test_llm_memory_recall_planner_falls_back_to_rules_on_error():
    planner = LlmMemoryRecallPlanner(provider=FakeRecallPlannerProvider(fail=True))

    plan = await planner.plan_recall("4번 장기기억 작업 이어서 해줘", workspace_key="team-a")

    assert plan.reason == "workspace_memory_needed"
    assert plan.planner_source == "rule_fallback"
    assert plan.fallback_reason == "llm_planner_error:RuntimeError"
    assert plan.planner_latency_ms is not None
    assert plan.filters()["metadata_categories"] == ["task_state", "fact"]


@pytest.mark.asyncio
async def test_llm_memory_recall_planner_times_out_to_rule_fallback():
    planner = LlmMemoryRecallPlanner(
        provider=FakeRecallPlannerProvider(delay_seconds=0.05),
        timeout_seconds=0.01,
    )

    plan = await planner.plan_recall("4번 장기기억 작업 이어서 해줘", workspace_key="team-a")

    assert plan.reason == "workspace_memory_needed"
    assert plan.planner_source == "rule_fallback"
    assert plan.fallback_reason == "llm_planner_timeout"
    assert plan.planner_latency_ms is not None


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
            "workspace_key": None,
            "store_type": None,
            "memory_type": None,
            "scope_type": None,
            "metadata_categories": None,
        }
    ]
    assert "client supplied context" not in task_input["persistent_memory_context"]
    assert "legacy client supplied context" not in str(task_input)
    assert "사용자는 회의 요약을 짧게 받는 것을 선호한다." in task_input["persistent_memory_context"]
    assert "hidden" not in task_input["persistent_memory_context"]
    recall_meta = task_input["memory_context_meta"]["recall"]
    assert recall_meta["status"] == "injected"
    assert recall_meta["source"] == "backend"
    assert recall_meta["query_present"] is True
    assert recall_meta["workspace_key_present"] is False
    assert recall_meta["count"] == 1
    assert recall_meta["memory_ids"] == [1]
    assert recall_meta["memory_types"] == ["PREFERENCE"]
    assert recall_meta["store_types"] == ["PROFILE"]
    assert recall_meta["scope_types"] == ["GLOBAL"]
    assert recall_meta["failed"] is False
    assert recall_meta["planner"]["should_recall"] is True
    assert recall_meta["planner"]["reason"] == "general_semantic_recall"
    assert recall_meta["planner"]["source"] == "rule"
    assert recall_meta["planner"]["filters"] == {}


@pytest.mark.asyncio
async def test_attach_persistent_memory_context_uses_llm_planner_when_available():
    memory_client = FakeMemoryClient([_memory("사용자는 MR 설명을 짧게 받는 것을 선호한다.")])
    planner = LlmMemoryRecallPlanner(
        provider=FakeRecallPlannerProvider(
            {
                "shouldRecall": True,
                "query": "MR 작성 선호",
                "reason": "사용자 MR 작성 선호 필요",
                "filters": {
                    "storeType": "USER_PROFILE",
                    "memoryType": "PREFERENCE",
                    "scopeType": "GLOBAL",
                    "metadataCategories": ["preference"],
                },
            }
        )
    )
    task_input = {"prompt": "MR 작업내용 정리해줘"}

    await attach_persistent_memory_context(
        app_state=SimpleNamespace(backend_memory_client=memory_client, memory_recall_planner=planner),
        task_input=task_input,
        user_id="7",
        query="MR 작업내용 정리해줘",
        workspace_key="team-a",
    )

    assert memory_client.calls == [
        {
            "user_id": "7",
            "query": "MR 작성 선호",
            "limit": 5,
            "workspace_key": None,
            "store_type": "USER_PROFILE",
            "memory_type": "PREFERENCE",
            "scope_type": "GLOBAL",
            "metadata_categories": ["preference"],
        }
    ]
    planner_meta = task_input["memory_context_meta"]["recall"]["planner"]
    assert planner_meta["should_recall"] is True
    assert planner_meta["reason"] == "사용자 MR 작성 선호 필요"
    assert planner_meta["source"] == "llm"
    assert planner_meta["latency_ms"] is not None
    assert planner_meta["filters"] == {
        "store_type": "USER_PROFILE",
        "memory_type": "PREFERENCE",
        "scope_type": "GLOBAL",
        "metadata_categories": ["preference"],
    }


@pytest.mark.asyncio
async def test_attach_persistent_memory_context_retries_user_preference_recall_without_query_when_empty():
    memory_client = EmptyThenMemoryClient([_memory("사용자는 점심 추천에서 샐러드나 생선 메뉴를 우선 선호한다.")])
    planner = LlmMemoryRecallPlanner(
        provider=FakeRecallPlannerProvider(
            {
                "shouldRecall": True,
                "query": "오늘 점심 뭐 먹을까?",
                "reason": "점심 추천은 사용자 음식 선호가 필요함",
                "filters": {
                    "storeType": "USER_PROFILE",
                    "memoryType": "PREFERENCE",
                    "scopeType": "GLOBAL",
                    "metadataCategories": ["preference"],
                },
            }
        )
    )
    task_input = {"prompt": "오늘 점심 뭐 먹을까?"}

    await attach_persistent_memory_context(
        app_state=SimpleNamespace(backend_memory_client=memory_client, memory_recall_planner=planner),
        task_input=task_input,
        user_id="7",
        query="오늘 점심 뭐 먹을까?",
    )

    assert memory_client.calls == [
        {
            "user_id": "7",
            "query": "오늘 점심 뭐 먹을까?",
            "limit": 5,
            "workspace_key": None,
            "store_type": "USER_PROFILE",
            "memory_type": "PREFERENCE",
            "scope_type": "GLOBAL",
            "metadata_categories": ["preference"],
        },
        {
            "user_id": "7",
            "query": None,
            "limit": 5,
            "workspace_key": None,
            "store_type": "USER_PROFILE",
            "memory_type": "PREFERENCE",
            "scope_type": "GLOBAL",
            "metadata_categories": ["preference"],
        },
    ]
    assert task_input["memory_context_meta"]["recall"]["status"] == "injected"
    assert task_input["memory_context_meta"]["recall"]["count"] == 1
    assert "샐러드나 생선" in task_input["persistent_memory_context"]


@pytest.mark.asyncio
async def test_attach_persistent_memory_context_skips_low_value_recall():
    memory_client = FakeMemoryClient([_memory("불러오면 안 되는 기억")])
    task_input = {"prompt": "안녕", "persistent_memory_context": "client supplied context"}

    await attach_persistent_memory_context(
        app_state=SimpleNamespace(backend_memory_client=memory_client),
        task_input=task_input,
        user_id="7",
        query="안녕",
        workspace_key="team-a",
    )

    assert memory_client.calls == []
    assert "persistent_memory_context" not in task_input
    assert task_input["memory_context_meta"]["recall"]["status"] == "skipped"
    assert task_input["memory_context_meta"]["recall"]["reason"] == "low_value_query"


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
    assert task_input["memory_context_meta"]["recall"]["planner"]["reason"] == "general_semantic_recall"


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
