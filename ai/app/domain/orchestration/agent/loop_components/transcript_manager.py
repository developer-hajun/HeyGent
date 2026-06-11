"""Transcript 관련 컴포넌트.

ToolCallingLoop의 transcript 관련 메서드들을 위임받는 thin adapter다.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.domain.orchestration.agent.tool_calling_loop import ToolCallingLoop


class TranscriptManager:
    """Transcript 관련 컴포넌트."""

    def __init__(self, loop: "ToolCallingLoop") -> None:
        self._loop = loop

    def ensure_transcript_session(self, **kwargs: Any) -> str | None:
        return self._loop._ensure_transcript_session(**kwargs)

    def load_transcript_messages(self, session_id: str | None) -> list[Any]:
        return self._loop._load_transcript_messages(session_id)

    def append_transcript_message(self, **kwargs: Any) -> None:
        return self._loop._append_transcript_message(**kwargs)
