# 장기기억 in-memory provider 는 추후 재설계 예정이라 현재는 전체 비활성화한다.
#
# from __future__ import annotations
#
# from collections import defaultdict
#
#
# class InMemoryProvider:
#     def __init__(self) -> None:
#         self._items: dict[str, list[str]] = defaultdict(list)
#
#     def recall(self, owner_key: str) -> list[str]:
#         return list(self._items.get(owner_key, []))
#
#     def remember(self, owner_key: str, item: str) -> None:
#         self._items[owner_key].append(item)
