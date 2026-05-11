from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from app.api.memory_observation import MEMORY_CONTEXT_META_KEY
from app.clients.backend_memory import BackendMemoryClientError

logger = logging.getLogger(__name__)

_MIN_OVERLAP_TOKENS = 2
_DEFAULT_USEFULNESS_SCORE = 0.6
_MAX_USEFULNESS_SCORE = 0.95
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9가-힣]{2,}")
_MEMORY_BLOCK_PATTERN = re.compile(r"(?ms)^- id: (?P<id>\d+)\n(?P<body>.*?)(?=^- id: |\Z)")
_FIELD_PATTERN = re.compile(r"(?m)^  (?P<key>summary|content): (?P<value>.+)$")
_STOPWORDS = {
    "사용자는",
    "사용자",
    "요청",
    "작업",
    "정리",
    "내용",
    "합니다",
    "있습니다",
    "그리고",
    "the",
    "and",
    "for",
    "with",
}


@dataclass(frozen=True, slots=True)
class _RecalledMemoryText:
    memory_id: int
    summary: str
    content: str


async def mark_used_recalled_memories(
    *,
    app_state: Any,
    task_input: dict[str, Any] | None,
    user_id: str,
    assistant_message: str | None,
    task_run_id: str | None = None,
) -> dict[str, Any]:
    """응답에 실제 반영된 것으로 보이는 recalled memory를 backend에 markUsed한다.

    1차 구현은 deterministic heuristic attribution을 사용한다. 실패해도 agent
    응답 저장 흐름을 깨지 않게 observation만 남긴다.
    """

    input_payload = dict(task_input or {})
    answer = str(assistant_message or "").strip()
    recalled_ids = _recalled_memory_ids(input_payload)
    if not recalled_ids:
        return _skipped("no_recalled_memories", task_run_id=task_run_id)
    if not answer:
        return _skipped("assistant_message_unavailable", task_run_id=task_run_id, recalled_ids=recalled_ids)

    memory_client = getattr(app_state, "backend_memory_client", None)
    if memory_client is None:
        return _skipped("memory_client_unavailable", task_run_id=task_run_id, recalled_ids=recalled_ids)

    memory_texts = _memory_texts_by_id(input_payload)
    attributions = _attribute_used_memories(
        recalled_ids=recalled_ids,
        memory_texts=memory_texts,
        assistant_message=answer,
    )
    if not attributions:
        return {
            "status": "skipped",
            "reason": "no_memory_attribution",
            "attempted": False,
            "recalled_memory_ids": recalled_ids,
            "used_memory_ids": [],
            "skipped_memory_ids": recalled_ids,
            "scores": {},
            "deduplicated": len(recalled_ids) != len(_raw_recalled_memory_ids(input_payload)),
            "task_run_id_present": bool(str(task_run_id or "").strip()),
        }

    used_ids: list[int] = []
    failed_ids: list[int] = []
    scores: dict[str, float] = {}
    for memory_id, score in attributions.items():
        try:
            await memory_client.mark_used(
                user_id=str(user_id),
                memory_id=memory_id,
                usefulness_score=score,
            )
        except BackendMemoryClientError:
            logger.warning("backend memory markUsed failed; continuing task completion", exc_info=True)
            failed_ids.append(memory_id)
            continue
        used_ids.append(memory_id)
        scores[str(memory_id)] = score

    skipped_ids = [memory_id for memory_id in recalled_ids if memory_id not in used_ids]
    status = "completed" if used_ids and not failed_ids else "partial" if used_ids else "failed"
    return {
        "status": status,
        "reason": "heuristic_attribution",
        "attempted": True,
        "recalled_memory_ids": recalled_ids,
        "used_memory_ids": used_ids,
        "skipped_memory_ids": skipped_ids,
        "failed_memory_ids": failed_ids,
        "scores": scores,
        "deduplicated": len(recalled_ids) != len(_raw_recalled_memory_ids(input_payload)),
        "task_run_id_present": bool(str(task_run_id or "").strip()),
        "failed": bool(failed_ids),
    }


def _attribute_used_memories(
    *,
    recalled_ids: list[int],
    memory_texts: dict[int, _RecalledMemoryText],
    assistant_message: str,
) -> dict[int, float]:
    answer_tokens = _tokens(assistant_message)
    if not answer_tokens:
        return {}

    attributions: dict[int, float] = {}
    for memory_id in recalled_ids:
        memory_text = memory_texts.get(memory_id)
        if memory_text is None:
            continue
        source_text = f"{memory_text.summary} {memory_text.content}".strip()
        source_tokens = _tokens(source_text)
        overlap = source_tokens.intersection(answer_tokens)
        if len(overlap) < _MIN_OVERLAP_TOKENS and not _has_direct_phrase(source_text, assistant_message):
            continue
        score = min(_MAX_USEFULNESS_SCORE, _DEFAULT_USEFULNESS_SCORE + len(overlap) * 0.05)
        attributions[memory_id] = round(score, 2)
    return attributions


def _recalled_memory_ids(input_payload: dict[str, Any]) -> list[int]:
    return list(dict.fromkeys(_raw_recalled_memory_ids(input_payload)))


def _raw_recalled_memory_ids(input_payload: dict[str, Any]) -> list[int]:
    raw_meta = input_payload.get(MEMORY_CONTEXT_META_KEY)
    recall = raw_meta.get("recall") if isinstance(raw_meta, dict) and isinstance(raw_meta.get("recall"), dict) else {}
    raw_ids = recall.get("memory_ids") if isinstance(recall, dict) else None
    if not isinstance(raw_ids, list):
        return []
    memory_ids: list[int] = []
    for value in raw_ids:
        if isinstance(value, int) and not isinstance(value, bool):
            memory_ids.append(value)
    return memory_ids


def _memory_texts_by_id(input_payload: dict[str, Any]) -> dict[int, _RecalledMemoryText]:
    prompt = str(input_payload.get("persistent_memory_context") or "")
    memory_texts: dict[int, _RecalledMemoryText] = {}
    for match in _MEMORY_BLOCK_PATTERN.finditer(prompt):
        memory_id = int(match.group("id"))
        fields = {
            field.group("key"): field.group("value").strip()
            for field in _FIELD_PATTERN.finditer(match.group("body"))
        }
        memory_texts[memory_id] = _RecalledMemoryText(
            memory_id=memory_id,
            summary=fields.get("summary", ""),
            content=fields.get("content", ""),
        )
    return memory_texts


def _tokens(value: str) -> set[str]:
    tokens: set[str] = set()
    for match in _TOKEN_PATTERN.finditer(value.lower()):
        token = match.group(0)
        if token not in _STOPWORDS:
            tokens.add(token)
    return tokens


def _has_direct_phrase(source_text: str, assistant_message: str) -> bool:
    normalized_answer = " ".join(assistant_message.lower().split())
    for token in _tokens(source_text):
        if len(token) >= 4 and token in normalized_answer:
            return True
    return False


def _skipped(reason: str, *, task_run_id: str | None, recalled_ids: list[int] | None = None) -> dict[str, Any]:
    recalled_ids = list(recalled_ids or [])
    return {
        "status": "skipped",
        "reason": reason,
        "attempted": False,
        "recalled_memory_ids": recalled_ids,
        "used_memory_ids": [],
        "skipped_memory_ids": recalled_ids,
        "scores": {},
        "deduplicated": False,
        "task_run_id_present": bool(str(task_run_id or "").strip()),
    }
