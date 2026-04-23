from __future__ import annotations

from collections import defaultdict


class InMemoryProvider:
    def __init__(self) -> None:
        self._items: dict[str, list[str]] = defaultdict(list)

    def recall(self, owner_key: str) -> list[str]:
        return list(self._items.get(owner_key, []))

    def remember(self, owner_key: str, item: str) -> None:
        self._items[owner_key].append(item)
