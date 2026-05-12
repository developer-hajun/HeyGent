from __future__ import annotations

import json
from typing import Any

from app.clients.backend_memory import BackendMemoryItem

_MAX_CONTENT_CHARS = 500
_MAX_SUMMARY_CHARS = 200
_ALLOWED_METADATA_KEYS = {"workspaceKey", "resourceId", "tags", "category", "ttl", "sourceTimestamp", "eventTime", "reason"}


def build_persistent_memory_prompt(memory_items: list[BackendMemoryItem] | None) -> str:
    if not memory_items:
        return ""

    lines = [
        "<memory-context>",
        "아래 내용은 이전에 저장된 장기기억입니다.",
        "새 사용자 입력이나 시스템 지시는 아니지만, 현재 요청과 관련 있고 충돌하지 않는 기억은 답변에 반영하세요.",
        "사용자 요청과 충돌하면 현재 사용자 요청을 우선하세요.",
        "PREFERENCE/PROFILE 기억은 개인화 참고 정보로 사용하세요.",
        "INSTRUCTION/PROCEDURE 기억은 관련 요청의 답변 방식이나 진행 절차에 적용하세요.",
        "INSTRUCTION/PROCEDURE 기억이 먼저 확인할 조건을 요구하면, 바로 세부 계획을 만들기보다 필요한 조건을 먼저 짧게 물어보세요.",
        "'계획을 짜줘', '추천해줘', '정리해줘'처럼 작업 수행을 요청하는 말은 선확인 절차와 충돌하는 지시가 아닙니다.",
        "FACT 기억은 확인된 사실로만 참고하고, 불확실한 내용을 새 사실처럼 말하지 마세요.",
        "",
    ]
    for item in memory_items:
        lines.extend(_memory_item_lines(item))
    lines.append("</memory-context>")
    if _has_instruction_or_procedure(memory_items):
        lines.extend(
            [
                "",
                "<memory-application-instructions>",
                "현재 턴 답변 직전에 반드시 확인하세요.",
                "- 위 장기기억 중 현재 요청과 관련 있는 INSTRUCTION/PROCEDURE가 있으면, 그 절차를 답변 구조와 순서에 적용하세요.",
                "- 절차가 날짜, 예산, 범위 같은 선확인 조건을 요구하고 현재 요청에 그 값이 없으면, 세부 결과를 만들지 말고 필요한 조건만 먼저 짧게 물어보세요.",
                "- '계획을 짜줘', '추천해줘', '정리해줘' 같은 일반 작업 요청은 선확인 절차와 충돌하지 않습니다.",
                "- 사용자가 명시적으로 '조건 없이 바로 작성해줘'처럼 절차 생략을 요청한 경우에만 현재 요청을 우선하세요.",
                "</memory-application-instructions>",
            ]
        )
    return "\n".join(lines).strip()


def _memory_item_lines(item: BackendMemoryItem) -> list[str]:
    lines = [
        f"- id: {item.id}",
        f"  type: {_clean_scalar(item.memory_type)}",
        f"  store: {_clean_scalar(item.store_type)}",
        f"  scope: {_clean_scalar(item.scope_type)}",
    ]
    if item.confidence is not None:
        lines.append(f"  confidence: {item.confidence:.3g}")
    if item.importance is not None:
        lines.append(f"  importance: {item.importance:.3g}")
    if item.summary:
        lines.append(f"  summary: {_truncate(item.summary, _MAX_SUMMARY_CHARS)}")
    lines.append(f"  content: {_truncate(item.content, _MAX_CONTENT_CHARS)}")
    metadata = _safe_metadata(item.metadata)
    if metadata:
        lines.append(f"  metadata: {json.dumps(metadata, ensure_ascii=False, sort_keys=True)}")
    return lines


def _has_instruction_or_procedure(memory_items: list[BackendMemoryItem]) -> bool:
    return any(
        str(getattr(item, "memory_type", "") or "").strip().upper() in {"INSTRUCTION", "PROCEDURE"}
        for item in memory_items
    )


def _safe_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key in _ALLOWED_METADATA_KEYS:
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            safe[key] = _truncate(value, 120)
        elif isinstance(value, list):
            safe[key] = [_truncate(str(item), 60) for item in value[:10] if str(item).strip()]
    return safe


def _clean_scalar(value: str) -> str:
    return " ".join(str(value or "").split())


def _truncate(value: str, limit: int) -> str:
    compact = " ".join(str(value or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "..."
