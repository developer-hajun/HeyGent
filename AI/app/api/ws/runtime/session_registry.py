from __future__ import annotations

from collections import defaultdict


class SessionRegistry:
    """세션별 task 구독 목록을 기억하는 얇은 레지스트리다."""

    def __init__(self) -> None:
        self._subscriptions: dict[str, set[str]] = defaultdict(set)

    def subscribe(self, session_id: str, task_run_id: str) -> None:
        self._subscriptions[session_id].add(task_run_id)

    def unsubscribe_all(self, session_id: str) -> None:
        self._subscriptions.pop(session_id, None)

    def get_subscriptions(self, session_id: str) -> set[str]:
        return set(self._subscriptions.get(session_id, set()))
