from __future__ import annotations

from collections import defaultdict


class ChannelDirectory:
    """Transport-level topic to connection mapping."""

    def __init__(self) -> None:
        self._topics: dict[str, set] = defaultdict(set)

    def add(self, topic: str, websocket) -> None:
        self._topics[topic].add(websocket)

    def discard(self, websocket) -> None:
        for sockets in self._topics.values():
            sockets.discard(websocket)

    def get(self, topic: str) -> set:
        return set(self._topics.get(topic, set()))
