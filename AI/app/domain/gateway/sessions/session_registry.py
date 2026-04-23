from __future__ import annotations

from collections import defaultdict

from app.domain.gateway.sessions.session import GatewaySession


class SessionRegistry:
    """Track websocket session subscription state independently from transport."""

    def __init__(self) -> None:
        self._sessions: dict[str, GatewaySession] = {}
        self._subscriptions: dict[str, set[str]] = defaultdict(set)

    def subscribe(self, session_id: str, topic: str) -> None:
        session = self._sessions.setdefault(session_id, GatewaySession(session_id=session_id))
        session.subscriptions.add(topic)
        self._subscriptions[session_id].add(topic)

    def unsubscribe_all(self, session_id: str) -> None:
        self._subscriptions.pop(session_id, None)
        self._sessions.pop(session_id, None)

    def get_subscriptions(self, session_id: str) -> set[str]:
        return set(self._subscriptions.get(session_id, set()))
