from __future__ import annotations


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, dict] = {}

    def put(self, session_id: str, payload: dict) -> None:
        self._sessions[session_id] = dict(payload)

    def get(self, session_id: str) -> dict | None:
        record = self._sessions.get(session_id)
        return dict(record) if record is not None else None
