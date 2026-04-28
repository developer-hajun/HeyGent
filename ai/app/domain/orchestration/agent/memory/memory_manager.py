# 장기기억 orchestration hook 은 추후 재설계 예정이라 현재는 전체 비활성화한다.
#
# from __future__ import annotations
#
#
# class MemoryManager:
#     """Minimal orchestration hook for future persistent-memory integration."""
#
#     def __init__(self, provider) -> None:
#         self.provider = provider
#
#     def recall(self, owner_key: str) -> list[str]:
#         return self.provider.recall(owner_key)
#
#     def remember(self, owner_key: str, item: str) -> None:
#         self.provider.remember(owner_key, item)
