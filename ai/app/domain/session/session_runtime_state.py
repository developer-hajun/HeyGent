from __future__ import annotations

from typing import Any


def get_system_prompt_snapshot(session: dict[str, Any], *, default: str = "") -> str:
    """product session의 stable system prompt snapshot을 읽는다.

    같은 공개 세션에서 provider prefix가 턴마다 갑자기 바뀌면 후속 답변 기준이 흔들린다.
    현재 서비스는 별도 prompt snapshot 저장소가 없으므로 metadata에 저장된 값을 우선 쓰고,
    없으면 빈 문자열을 명시적으로 사용해 이전 대화 history와 runtime prompt의 역할을 분리한다.
    """

    metadata = session.get("metadata") if isinstance(session.get("metadata"), dict) else {}
    value = metadata.get("system_prompt_snapshot") or metadata.get("system_prompt") or session.get("system_prompt")
    if isinstance(value, str):
        return value
    return default
