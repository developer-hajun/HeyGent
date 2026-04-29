from __future__ import annotations

import inspect
from typing import get_type_hints

from app.domain.orchestration.agent.loop import TaskEngine
from app.domain.orchestration.agent.tool_calling_loop import ToolCallingLoopExecutor
from app.domain.session import SessionStore, TranscriptStore
from app.domain.session.sessions import TranscriptStore as SessionsTranscriptStore
from app.tools.runtime.local_tool_runtime import LocalToolRuntime


def test_sqlite_session_store_implements_transcript_store(tmp_path):
    store = SessionStore(tmp_path / "sessions.db")
    try:
        assert isinstance(store, TranscriptStore)
    finally:
        store.close()


def test_sqlite_session_store_satisfies_transcript_semantic_contract(tmp_path):
    store = SessionStore(tmp_path / "sessions.db")
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
        search_results = store.search_sessions("계약", limit=5)
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


def test_transcript_store_is_exported_from_session_packages():
    assert SessionsTranscriptStore is TranscriptStore


def test_runtime_and_agent_loop_depend_on_transcript_store_protocol():
    loop_hints = get_type_hints(ToolCallingLoopExecutor.__init__)
    runtime_hints = get_type_hints(LocalToolRuntime.__init__)
    session_store_return = inspect.signature(TaskEngine._session_store_from_executor).return_annotation

    assert "TranscriptStore" in str(loop_hints["session_store"])
    assert "TranscriptStore" in str(runtime_hints["session_store"])
    assert "TranscriptStore" in str(session_store_return)
