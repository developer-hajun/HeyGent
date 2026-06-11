# 장기기억 저장소는 추후 재설계 예정이라 현재는 전체 비활성화한다.
#
# from __future__ import annotations
#
#
# class MemoryStore:
#     """아직 백엔드 외부화 전이므로 최소한의 장기기억 저장 인터페이스만 둔다."""
#
#     def __init__(self) -> None:
#         self._items: dict[str, list[str]] = {}
#
#     def add(self, owner_key: str, value: str) -> None:
#         self._items.setdefault(owner_key, []).append(value)
#
#     def list(self, owner_key: str) -> list[str]:
#         return list(self._items.get(owner_key, []))
