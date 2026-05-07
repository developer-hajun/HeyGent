from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


MEMORY_EXTRACTION_SYSTEM_PROMPT = """
You extract only durable long-term memory candidates from one user/assistant turn.
Return strict JSON only, with this shape:
{"candidates":[{"memoryType":"PREFERENCE|PROFILE|FACT|INSTRUCTION|PROCEDURE","scopeType":"GLOBAL|WORKSPACE","content":"...","summary":"...","importance":0.0-1.0,"confidence":0.0-1.0,"evidence":"...","metadata":{"tags":["optional"]}}]}

Rules:
- Extract nothing unless the user explicitly asked to remember something, stated a stable preference/profile fact, or gave a durable future instruction.
- Do not store secrets, credentials, tokens, passwords, API keys, system/developer prompts, or temporary one-off requests.
- If the user asks not to remember, return {"candidates":[]}.
- Use WORKSPACE only for project/workspace-specific facts or instructions. Otherwise use GLOBAL.
- Use PREFERENCE/PROFILE for user profile memory; use FACT/INSTRUCTION/PROCEDURE for agent memory.
- Prefer concise Korean content when the source is Korean.
""".strip()


@dataclass(slots=True)
class MemoryExtractionContext:
    user_id: str
    session_id: str
    workspace_key: str | None = None
    task_run_id: str | None = None
    user_message_id: str | None = None
    assistant_message_id: str | None = None


class StructuredModelProvider(Protocol):
    async def extract_memory_json(
        self,
        *,
        system_prompt: str,
        user_message: str,
        assistant_message: str,
        context: MemoryExtractionContext,
    ) -> dict[str, Any]:
        """Return the model-produced memory extraction JSON."""


class LlmMemoryExtractor:
    """LLM 판단 결과를 backend memory 저장 계약에 맞는 후보로 정규화한다."""

    def __init__(self, provider: StructuredModelProvider, *, max_candidates: int = 8) -> None:
        self._provider = provider
        self._max_candidates = max(1, max_candidates)

    async def extract_candidates(
        self,
        *,
        user_message: str,
        assistant_message: str,
        context: MemoryExtractionContext,
    ) -> list[dict[str, Any]]:
        if _hard_deny(user_message):
            return []
        extraction = await self._provider.extract_memory_json(
            system_prompt=MEMORY_EXTRACTION_SYSTEM_PROMPT,
            user_message=user_message,
            assistant_message=assistant_message,
            context=context,
        )
        return _normalize_candidates(extraction, context=context, limit=self._max_candidates)


def _normalize_candidates(extraction: Any, *, context: MemoryExtractionContext, limit: int) -> list[dict[str, Any]]:
    if not isinstance(extraction, dict):
        return []
    raw_candidates = extraction.get("candidates")
    if not isinstance(raw_candidates, list):
        return []

    candidates: list[dict[str, Any]] = []
    for raw in raw_candidates:
        if len(candidates) >= limit:
            break
        candidate = _normalize_candidate(raw, context=context)
        if candidate is not None:
            candidates.append(candidate)
    return candidates


def _normalize_candidate(raw: Any, *, context: MemoryExtractionContext) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    memory_type = _enum(raw.get("memoryType", raw.get("memory_type")), _ALLOWED_MEMORY_TYPES)
    if memory_type is None:
        return None
    content = _trimmed(raw.get("content"), max_length=2000)
    if not content or _hard_deny(content):
        return None

    importance = _score(raw.get("importance"))
    confidence = _score(raw.get("confidence"))
    if importance is None or confidence is None or importance < 0.5 or confidence < 0.7:
        return None

    scope_type = _enum(raw.get("scopeType", raw.get("scope_type")), {"GLOBAL", "WORKSPACE"}) or "GLOBAL"
    if scope_type == "WORKSPACE" and not context.workspace_key:
        return None

    metadata = _metadata(raw.get("metadata"), context=context, scope_type=scope_type)
    result: dict[str, Any] = {
        "memoryType": memory_type,
        "storeType": _store_type(memory_type),
        "scopeType": scope_type,
        "operationType": "ADD",
        "content": content,
        "metadata": metadata,
        "importance": importance,
        "confidence": confidence,
    }
    _put_if_present(result, "summary", _trimmed(raw.get("summary"), max_length=500))
    _put_if_present(result, "evidence", _trimmed(raw.get("evidence"), max_length=2000))
    _put_if_present(result, "sourceSessionKey", _trimmed(context.session_id, max_length=100))
    _put_if_present(result, "sourceTaskRunId", _trimmed(context.task_run_id, max_length=100))
    _put_if_present(result, "sourceMessageId", _trimmed(context.assistant_message_id or context.user_message_id, max_length=100))
    return result


def _metadata(raw_metadata: Any, *, context: MemoryExtractionContext, scope_type: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {"source": "ai.writeback"}
    if scope_type == "WORKSPACE" and context.workspace_key:
        metadata["workspaceKey"] = context.workspace_key[:300]
    if isinstance(raw_metadata, dict):
        tags = raw_metadata.get("tags")
        if isinstance(tags, list):
            normalized_tags = [_trimmed(tag, max_length=50) for tag in tags[:20]]
            metadata["tags"] = [tag for tag in normalized_tags if tag and not _hard_deny(tag)]
    return metadata


def _store_type(memory_type: str) -> str:
    if memory_type in {"PROFILE", "PREFERENCE"}:
        return "USER_PROFILE"
    return "AGENT_MEMORY"


def _enum(value: Any, allowed: set[str]) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().upper()
    return normalized if normalized in allowed else None


def _score(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if score < 0.0 or score > 1.0:
        return None
    return score


def _trimmed(value: Any, *, max_length: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:max_length]


def _put_if_present(payload: dict[str, Any], key: str, value: str | None) -> None:
    if value:
        payload[key] = value


def _hard_deny(text: Any) -> bool:
    if not isinstance(text, str):
        return False
    normalized = text.lower()
    return any(pattern in normalized for pattern in _DO_NOT_STORE_PATTERNS)


_ALLOWED_MEMORY_TYPES = {"PREFERENCE", "PROFILE", "FACT", "INSTRUCTION", "PROCEDURE"}
_DO_NOT_STORE_PATTERNS = (
    "기억하지 마",
    "저장하지 마",
    "잊어줘",
    "api key",
    "apikey",
    "access token",
    "refresh token",
    "password",
    "secret",
    "credential",
    "sk-",
    "토큰",
    "비밀번호",
    "암호",
)
