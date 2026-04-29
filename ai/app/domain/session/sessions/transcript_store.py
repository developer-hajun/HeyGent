from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class TranscriptStore(Protocol):
    """agent.loop transcript와 세션 검색 저장소가 지켜야 하는 계약이다."""

    def create_session(
        self,
        *,
        session_id: str,
        session_key: str,
        source: str,
        user_id: str | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
        parent_session_id: str | None = None,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """새 transcript/session 레코드를 만든다."""
        ...

    def end_session(self, session_id: str, *, end_reason: str | None = None) -> None:
        """열린 transcript/session을 종료 상태로 표시한다."""
        ...

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """식별자로 transcript/session 메타데이터를 조회한다."""
        ...

    def list_sessions(
        self,
        owner: str | None = None,
        *,
        user_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """owner 범위의 transcript/session 목록을 최근 업데이트 순서로 조회한다."""
        ...

    def get_latest_session_by_key(self, session_key: str, *, owner: str | None = None) -> dict[str, Any] | None:
        """동일 owner/session_key 중 가장 최근 transcript/session을 조회한다."""
        ...

    def append_message(
        self,
        *,
        session_id: str,
        role: str,
        content: str | None,
        tool_name: str | None = None,
        tool_call_id: str | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        finish_reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """transcript/session에 메시지 한 건을 추가한다."""
        ...

    def list_messages(self, session_id: str, *, limit: int | None = None) -> list[dict[str, Any]]:
        """저장된 메시지를 provider replay 순서로 조회한다."""
        ...

    def search_sessions(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        """메시지 본문 기준으로 transcript/session을 검색한다."""
        ...

    def close(self) -> None:
        """저장소 연결과 관련 자원을 닫는다."""
        ...
