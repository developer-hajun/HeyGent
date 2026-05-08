from __future__ import annotations

import inspect
from typing import get_type_hints

from app.domain.orchestration.agent.loop import TaskEngine
from app.domain.orchestration.agent.tool_calling_loop import ToolCallingLoopHandler
from app.domain.session import TranscriptStore
from app.domain.session.sessions import TranscriptStore as SessionsTranscriptStore
from app.storage.postgres import PostgresSessionStore
from app.tools.runtime.local_tool_runtime import LocalToolRuntime
from tests.fakes import InMemoryTranscriptStore


def test_in_memory_session_store_implements_transcript_store():
    store = InMemoryTranscriptStore()

    assert isinstance(store, TranscriptStore)


def test_postgres_session_store_implements_transcript_store():
    store = PostgresSessionStore(lambda: None)

    assert isinstance(store, TranscriptStore)


def test_in_memory_session_store_satisfies_transcript_semantic_contract():
    store = InMemoryTranscriptStore()
    try:
        session_id = store.create_session(
            session_id="session_contract",
            session_key="contract-key",
            source="agent.loop",
            user_id="tester",
            model="gpt-test",
            title="계약 테스트",
            metadata={"task_run_id": "task_contract"},
        )

        message_id = store.append_message(
            session_id=session_id,
            role="assistant",
            content="검색 가능한 계약 메시지",
            tool_calls=[{"id": "call_1", "name": "terminal.run", "arguments": {}}],
            finish_reason="tool_calls",
            metadata={"turn": 1},
        )
        store.end_session(session_id, end_reason="completed")

        latest = store.get_latest_session_by_key("contract-key")
        messages = store.list_messages(session_id)
        search_results = store.search_transcript_sessions("계약", owner_key="tester", limit=5)
        ended = store.get_session(session_id)

        assert message_id > 0
        assert latest is not None
        assert latest["id"] == session_id
        assert latest["metadata"] == {"task_run_id": "task_contract"}
        assert messages[0]["tool_calls"] == [{"id": "call_1", "name": "terminal.run", "arguments": {}}]
        assert messages[0]["metadata"] == {"turn": 1}
        assert search_results[0]["id"] == session_id
        assert ended is not None
        assert ended["end_reason"] == "completed"
    finally:
        store.close()


def test_in_memory_session_store_appends_user_message_and_starts_task_atomically():
    store = InMemoryTranscriptStore()
    store.create_session(
        session_id="public_session_contract",
        session_key="public_session_contract",
        source="api.session",
        user_id="owner-a",
        metadata={"source": "api.session"},
    )

    result = store.append_user_message_and_start_task(
        owner_key="owner-a",
        session_id="public_session_contract",
        content="이전 맥락을 이어서 처리해줘",
        client_message_id="client-contract-1",
        task_run_id="task_contract_1",
        base_history_version=0,
    )
    duplicate = store.append_user_message_and_start_task(
        owner_key="owner-a",
        session_id="public_session_contract",
        content="이전 맥락을 이어서 처리해줘",
        client_message_id="client-contract-1",
        task_run_id="task_contract_duplicate",
        base_history_version=1,
    )

    assert result["duplicate"] is False
    assert result["message_id"] == 1
    assert result["after_user_message_version"] == 1
    assert result["completion_expected_version"] == 1
    assert duplicate["duplicate"] is True
    assert duplicate["task_run_id"] == "task_contract_1"
    assert len(store.list_messages("public_session_contract")) == 1
    assert store.get_session("public_session_contract")["running_task_run_id"] == "task_contract_1"


def test_in_memory_session_store_finishes_task_with_history_version_guard():
    store = InMemoryTranscriptStore()
    store.create_session(
        session_id="public_session_finish",
        session_key="public_session_finish",
        source="api.session",
        user_id="owner-a",
        metadata={"source": "api.session"},
    )
    started = store.append_user_message_and_start_task(
        owner_key="owner-a",
        session_id="public_session_finish",
        content="질문",
        client_message_id="client-finish-1",
        task_run_id="task_finish_1",
        base_history_version=0,
    )

    finished = store.append_assistant_message_and_finish_task(
        owner_key="owner-a",
        session_id="public_session_finish",
        task_run_id="task_finish_1",
        content="답변",
        completion_expected_version=started["completion_expected_version"],
        status="COMPLETED",
    )

    assert finished["message_id"] == 2
    assert finished["completion_result_version"] == 2
    session = store.get_session("public_session_finish")
    assert session["running_task_run_id"] is None
    assert session["history_version"] == 2


def test_public_session_search_requires_owner_and_hides_internal_transcripts():
    store = InMemoryTranscriptStore()
    store.create_session(
        session_id="public_search_session",
        session_key="public_search_session",
        source="api.session",
        user_id="owner-a",
        metadata={"source": "api.session"},
    )
    store.create_session(
        session_id="internal_search_session",
        session_key="public_search_session",
        source="agent.loop",
        user_id="owner-a",
        metadata={"source": "agent.loop"},
    )
    store.append_message(session_id="public_search_session", role="user", content="검색 가능한 공개 메시지")
    store.append_message(session_id="internal_search_session", role="assistant", content="검색 가능한 내부 메시지")

    public_results = store.search_public_sessions("검색", owner_key="owner-a")
    transcript_results = store.search_transcript_sessions("검색", owner_key="owner-a")

    assert [item["id"] for item in public_results] == ["public_search_session"]
    assert [item["id"] for item in transcript_results] == ["internal_search_session"]

    try:
        store.search_transcript_sessions("검색", owner_key="")
    except ValueError as error:
        assert "owner_key is required" in str(error)
    else:
        raise AssertionError("owner 없는 transcript 검색은 거절되어야 한다")


def test_transcript_store_is_exported_from_session_packages():
    assert SessionsTranscriptStore is TranscriptStore


def test_runtime_and_agent_loop_depend_on_transcript_store_protocol():
    loop_hints = get_type_hints(ToolCallingLoopHandler.__init__)
    runtime_hints = get_type_hints(LocalToolRuntime.__init__)
    session_store_return = inspect.signature(TaskEngine._session_store_from_handler).return_annotation

    assert "TranscriptStore" in str(loop_hints["session_store"])
    assert "TranscriptStore" in str(runtime_hints["session_store"])
    assert "TranscriptStore" in str(session_store_return)
