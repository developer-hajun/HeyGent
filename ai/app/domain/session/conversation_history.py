from __future__ import annotations

from typing import Any


def build_conversation_history(
    rows: list[dict[str, Any]],
    max_messages: int = 24,
    max_chars_per_message: int = 6000,
) -> list[dict[str, str]]:
    """공개 세션 메시지를 모델 입력용 대화 history로 변환한다.

    공개 세션은 user/assistant 대화만 이어쓰기 기준으로 삼는다. tool/internal 메시지는
    내부 실행 transcript의 재개 재료이므로 여기 섞이면 오래된 실행 상태가 다음 턴에 재사용될 수 있다.
    """

    if max_messages <= 0:
        return []

    selected: list[dict[str, str]] = []
    for row in rows:
        role = str(row.get("role") or "").strip()
        if role not in {"user", "assistant"}:
            continue

        content = str(row.get("content") or "").strip()
        if not content:
            continue

        if max_chars_per_message >= 0 and len(content) > max_chars_per_message:
            content = content[:max_chars_per_message].rstrip()
            content = f"{content}\n[이전 메시지가 길어 일부를 생략했습니다.]"

        selected.append({"role": role, "content": content})

    if len(selected) > max_messages:
        return selected[-max_messages:]
    return selected
