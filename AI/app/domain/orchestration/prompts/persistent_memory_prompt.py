# 장기기억 prompt 조립은 추후 재설계 예정이라 현재는 전체 비활성화한다.
#
# from __future__ import annotations
#
#
# def build_persistent_memory_prompt(*, memory_items: list[str] | None = None) -> str:
#     if not memory_items:
#         return ""
#     return "장기 기억:\n" + "\n".join(f"- {item}" for item in memory_items)
