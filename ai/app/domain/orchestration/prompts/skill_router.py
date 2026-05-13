from __future__ import annotations

import re
from typing import Any


MATTERMOST_SEND_SKILL = "mattermost-send"

_MATTERMOST_TARGET_PATTERN = re.compile(
    r"(\bmattermost\b|매터모스트|\bmm\b|backend|frontend|백엔드|프론트엔드|e\d+)",
    re.IGNORECASE,
)
_SEND_VERB_PATTERN = re.compile(
    r"(보내|전송|공유|올려|공지|send|post|share)",
    re.IGNORECASE,
)


def route_skill_hints(input_payload: dict[str, Any] | None) -> dict[str, Any]:
    """사용자 요청 의도에 맞는 skill hint를 자동 주입한다.

    명시적인 사용자의 skill_hints는 유지하고, 라우터가 감지한 skill만 뒤에 더한다.
    """

    payload = dict(input_payload or {})
    hints = [str(item).strip() for item in payload.get("skill_hints") or [] if str(item).strip()]
    prompt = _prompt_text(payload)
    if _is_mattermost_send_intent(prompt):
        hints.append(MATTERMOST_SEND_SKILL)
    if hints:
        payload["skill_hints"] = list(dict.fromkeys(hints))
    return payload


def _prompt_text(payload: dict[str, Any]) -> str:
    parts = [
        payload.get("prompt"),
        payload.get("observed_step_title"),
        payload.get("observed_step_goal"),
    ]
    return "\n".join(str(part) for part in parts if part)


def _is_mattermost_send_intent(text: str) -> bool:
    if not text.strip():
        return False
    return bool(_MATTERMOST_TARGET_PATTERN.search(text) and _SEND_VERB_PATTERN.search(text))
