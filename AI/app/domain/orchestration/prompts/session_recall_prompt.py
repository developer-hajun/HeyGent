# 세션 recall prompt 조립은 추후 재설계 예정이라 현재는 전체 비활성화한다.
#
# from __future__ import annotations
#
#
# def build_session_recall_prompt(*, items: list[str] | None = None) -> str:
#     if not items:
#         return ""
#     return "과거 세션 회수:\n" + "\n".join(f"- {item}" for item in items)
