from __future__ import annotations


class HeartbeatRegistry:
    def __init__(self) -> None:
        self._timestamps: dict[str, str] = {}

    def mark(self, session_id: str, timestamp: str) -> None:
        self._timestamps[session_id] = timestamp
