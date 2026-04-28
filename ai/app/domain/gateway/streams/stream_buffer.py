from __future__ import annotations


class StreamBuffer:
    def __init__(self) -> None:
        self._items: list[dict] = []

    def push(self, payload: dict) -> None:
        self._items.append(dict(payload))

    def drain(self) -> list[dict]:
        items = list(self._items)
        self._items.clear()
        return items
