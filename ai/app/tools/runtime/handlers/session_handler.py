"""Session tool 핸들러.

session.record / session.search 도구의 구현체.
LocalToolRuntime이 소유하고 디스패치 테이블에서 호출한다.
"""
from __future__ import annotations

from typing import Any

from app.core.utils.ids import new_id
from app.tools.runtime.handlers.skill_handler import _optional_text


class SessionHandler:
    """session.record / session.search tool 구현체.

    Args:
        session_store: TranscriptStore 구현체.
        owner_key: 요청 소유자 식별자.
        tool_error_fn: _tool_error 유틸리티 (LocalToolRuntime에서 주입).
    """

    def __init__(self, *, session_store: Any, owner_key: str | None, tool_error_fn: Any) -> None:
        self._session_store = session_store
        self._owner_key = owner_key
        self._tool_error = tool_error_fn

    def record_session_message(self, args: dict[str, Any]) -> dict[str, object]:
        session_key = str(args.get("session_key") or "runtime-probe")
        latest = self._session_store.get_latest_session_by_key(session_key)
        if latest is None:
            session_id = new_id("session")
            self._session_store.create_session(
                session_id=session_id,
                session_key=session_key,
                source=str(args.get("source") or "runtime-probe"),
                title=str(args.get("title") or session_key),
            )
        else:
            session_id = str(latest["id"])

        message_id = self._session_store.append_message(
            session_id=session_id,
            role=str(args.get("role") or "user"),
            content=str(args.get("content") or ""),
        )
        return {
            "session_id": session_id,
            "message_id": message_id,
            "session_key": session_key,
        }

    def search_sessions(self, args: dict[str, Any]) -> dict[str, object]:
        limit = int(args.get("limit") or 5)
        if not self._owner_key:
            return self._tool_error(
                code="owner_required",
                message="session.search requires a bound owner",
                tool_name="session.search",
            )
        results = self._session_store.search_transcript_sessions(
            str(args.get("query") or ""),
            owner_key=self._owner_key,
            limit=limit,
        )
        return {
            "count": len(results),
            "items": results,
        }
