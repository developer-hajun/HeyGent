from __future__ import annotations


class MemoryStore:
    def __init__(self) -> None:
        self._items: dict[str, list[str]] = {}

    def add(self, owner_key: str, value: str) -> None:
        self._items.setdefault(owner_key, []).append(value)

    def list(self, owner_key: str) -> list[str]:
        return list(self._items.get(owner_key, []))
