from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.api.memory_observation import MEMORY_CONTEXT_META_KEY, build_recall_observation
from app.clients.backend_memory import BackendMemoryClientError
from app.domain.orchestration.prompts.persistent_memory_prompt import build_persistent_memory_prompt

logger = logging.getLogger(__name__)

DEFAULT_MEMORY_RECALL_LIMIT = 5
MEMORY_CONTEXT_KEYS = ("persistent_memory_context", "memory_context")
MEMORY_RECALL_QUERY_KEYS = ("prompt", "message", "query", "content", "text", "subject", "title")


@dataclass(frozen=True, slots=True)
class MemoryRecallPlan:
    should_recall: bool
    query: str | None
    reason: str
    limit: int = DEFAULT_MEMORY_RECALL_LIMIT
    store_type: str | None = None
    memory_type: str | None = None
    scope_type: str | None = None
    workspace_key: str | None = None
    metadata_categories: tuple[str, ...] = ()

    def filters(self) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        _put_if_present(filters, "store_type", self.store_type)
        _put_if_present(filters, "memory_type", self.memory_type)
        _put_if_present(filters, "scope_type", self.scope_type)
        _put_if_present(filters, "workspace_key", self.workspace_key)
        if self.metadata_categories:
            filters["metadata_categories"] = list(self.metadata_categories)
        return filters


def clear_client_memory_context(task_input: dict[str, Any]) -> None:
    for key in MEMORY_CONTEXT_KEYS:
        task_input.pop(key, None)
    task_input.pop(MEMORY_CONTEXT_META_KEY, None)


def select_memory_recall_query(input_payload: dict[str, Any]) -> str | None:
    for key in MEMORY_RECALL_QUERY_KEYS:
        value = input_payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def plan_memory_recall(
    query: str | None,
    *,
    workspace_key: str | None = None,
    limit: int = DEFAULT_MEMORY_RECALL_LIMIT,
) -> MemoryRecallPlan:
    normalized_query = str(query or "").strip()
    if not normalized_query:
        return MemoryRecallPlan(
            should_recall=False,
            query=None,
            reason="query_unavailable",
            limit=limit,
        )

    normalized_workspace_key = str(workspace_key or "").strip() or None
    compact = " ".join(normalized_query.lower().split())
    if _is_low_value_recall_query(compact):
        return MemoryRecallPlan(
            should_recall=False,
            query=normalized_query,
            reason="low_value_query",
            limit=limit,
        )

    wants_preference = _contains_any(compact, _PREFERENCE_HINTS)
    wants_profile = _contains_any(compact, _PROFILE_HINTS)
    wants_workspace = _contains_any(compact, _WORKSPACE_HINTS)
    wants_procedure = _contains_any(compact, _PROCEDURE_HINTS)
    wants_reason = _contains_any(compact, _REASON_HINTS)
    wants_event = _contains_any(compact, _EVENT_HINTS)

    if wants_preference and not (wants_workspace or wants_procedure or wants_reason or wants_event):
        return MemoryRecallPlan(
            should_recall=True,
            query=normalized_query,
            reason="user_preference_needed",
            limit=limit,
            store_type="USER_PROFILE",
            memory_type="PREFERENCE",
            scope_type="GLOBAL",
            metadata_categories=("preference",),
        )

    if wants_profile and not (wants_workspace or wants_procedure or wants_reason or wants_event):
        return MemoryRecallPlan(
            should_recall=True,
            query=normalized_query,
            reason="user_profile_needed",
            limit=limit,
            store_type="USER_PROFILE",
            memory_type="PROFILE",
            scope_type="GLOBAL",
            metadata_categories=("profile",),
        )

    if wants_workspace:
        categories = _workspace_categories(
            wants_procedure=wants_procedure,
            wants_reason=wants_reason,
            wants_event=wants_event,
        )
        return MemoryRecallPlan(
            should_recall=True,
            query=normalized_query,
            reason="workspace_memory_needed",
            limit=limit,
            store_type="AGENT_MEMORY",
            memory_type="PROCEDURE" if wants_procedure and not (wants_reason or wants_event) else "FACT",
            scope_type="WORKSPACE" if normalized_workspace_key else None,
            workspace_key=normalized_workspace_key,
            metadata_categories=categories,
        )

    if wants_procedure:
        return MemoryRecallPlan(
            should_recall=True,
            query=normalized_query,
            reason="procedure_memory_needed",
            limit=limit,
            store_type="AGENT_MEMORY",
            memory_type="PROCEDURE",
            metadata_categories=("procedure", "instruction"),
        )

    if wants_reason:
        return MemoryRecallPlan(
            should_recall=True,
            query=normalized_query,
            reason="reason_memory_needed",
            limit=limit,
            store_type="AGENT_MEMORY",
            memory_type="FACT",
            metadata_categories=("reason", "fact"),
        )

    if wants_event:
        return MemoryRecallPlan(
            should_recall=True,
            query=normalized_query,
            reason="event_memory_needed",
            limit=limit,
            store_type="AGENT_MEMORY",
            memory_type="FACT",
            metadata_categories=("event", "task_state", "fact"),
        )

    return MemoryRecallPlan(
        should_recall=True,
        query=normalized_query,
        reason="general_semantic_recall",
        limit=limit,
    )


async def attach_persistent_memory_context(
    *,
    app_state: Any,
    task_input: dict[str, Any],
    user_id: str,
    query: str | None,
    workspace_key: str | None = None,
    limit: int = DEFAULT_MEMORY_RECALL_LIMIT,
) -> None:
    clear_client_memory_context(task_input)
    recall_plan = plan_memory_recall(query, workspace_key=workspace_key, limit=limit)
    if not recall_plan.should_recall:
        _set_recall_meta(
            task_input,
            _with_recall_plan(
                build_recall_observation(
                    status="skipped",
                    query=recall_plan.query,
                    workspace_key=recall_plan.workspace_key,
                    reason=recall_plan.reason,
                ),
                recall_plan,
            ),
        )
        return

    normalized_query = str(recall_plan.query or "").strip()
    if not normalized_query:
        _set_recall_meta(
            task_input,
            _with_recall_plan(
                build_recall_observation(
                    status="skipped",
                    query=query,
                    workspace_key=workspace_key,
                    reason="query_unavailable",
                ),
                recall_plan,
            ),
        )
        return

    memory_client = getattr(app_state, "backend_memory_client", None)
    if memory_client is None:
        _set_recall_meta(
            task_input,
            _with_recall_plan(
                build_recall_observation(
                    status="skipped",
                    query=normalized_query,
                    workspace_key=recall_plan.workspace_key,
                    reason="memory_client_unavailable",
                ),
                recall_plan,
            ),
        )
        return

    try:
        memories = await memory_client.recall(
            user_id=str(user_id),
            query=normalized_query,
            limit=recall_plan.limit,
            workspace_key=recall_plan.workspace_key,
            store_type=recall_plan.store_type,
            memory_type=recall_plan.memory_type,
            scope_type=recall_plan.scope_type,
            metadata_categories=list(recall_plan.metadata_categories) or None,
        )
    except BackendMemoryClientError:
        logger.warning("backend memory recall failed; continuing without persistent memory context", exc_info=True)
        _set_recall_meta(
            task_input,
            _with_recall_plan(
                build_recall_observation(
                    status="failed",
                    query=normalized_query,
                    workspace_key=recall_plan.workspace_key,
                    reason="backend_memory_client_error",
                    failed=True,
                ),
                recall_plan,
            ),
        )
        return

    memory_prompt = build_persistent_memory_prompt(memories)
    _set_recall_meta(
        task_input,
        _with_recall_plan(
            build_recall_observation(
                status="injected" if memory_prompt else "empty",
                query=normalized_query,
                workspace_key=recall_plan.workspace_key,
                memories=memories,
            ),
            recall_plan,
        ),
    )
    if memory_prompt:
        task_input["persistent_memory_context"] = memory_prompt


def _set_recall_meta(task_input: dict[str, Any], recall_meta: dict[str, Any]) -> None:
    task_input[MEMORY_CONTEXT_META_KEY] = {"recall": recall_meta}


def _with_recall_plan(recall_meta: dict[str, Any], recall_plan: MemoryRecallPlan) -> dict[str, Any]:
    enriched = dict(recall_meta)
    enriched["planner"] = {
        "should_recall": recall_plan.should_recall,
        "reason": recall_plan.reason,
        "filters": recall_plan.filters(),
    }
    return enriched


def _workspace_categories(*, wants_procedure: bool, wants_reason: bool, wants_event: bool) -> tuple[str, ...]:
    categories: list[str] = []
    if wants_procedure:
        categories.extend(["procedure", "instruction"])
    if wants_reason:
        categories.append("reason")
    if wants_event:
        categories.append("event")
    categories.extend(["task_state", "fact"])
    return tuple(dict.fromkeys(categories))


def _is_low_value_recall_query(compact_query: str) -> bool:
    return compact_query in _LOW_VALUE_RECALL_QUERIES or any(
        compact_query.startswith(prefix) and len(compact_query) <= len(prefix) + 4
        for prefix in _LOW_VALUE_RECALL_PREFIXES
    )


def _contains_any(text: str, hints: tuple[str, ...]) -> bool:
    return any(hint in text for hint in hints)


def _put_if_present(payload: dict[str, Any], key: str, value: str | None) -> None:
    if value:
        payload[key] = value


_LOW_VALUE_RECALL_QUERIES = {
    "안녕",
    "안녕하세요",
    "고마워",
    "감사",
    "감사합니다",
    "thanks",
    "thank you",
    "hi",
    "hello",
}
_LOW_VALUE_RECALL_PREFIXES = ("안녕", "고마", "감사", "thanks", "thank you", "hi", "hello")
_PREFERENCE_HINTS = (
    "선호",
    "말투",
    "톤",
    "형식",
    "짧게",
    "길게",
    "앞으로",
    "복붙",
    "jira",
    "지라",
    "mr",
)
_PROFILE_HINTS = ("내 담당", "내 역할", "프로필", "나는 ", "제가 ")
_WORKSPACE_HINTS = (
    "이어서",
    "아까",
    "방금",
    "기존",
    "현재 구현",
    "구현",
    "브랜치",
    "코드",
    "문서",
    "docs",
    "logs",
    "계획",
    "장기기억",
    "작업",
    "테스트",
    "검증",
    "backend",
    "프론트",
)
_PROCEDURE_HINTS = ("작업해줘", "docs/logs", "로그", "mr", "절차", "방법")
_REASON_HINTS = ("왜", "이유", "근거")
_EVENT_HINTS = ("언제", "지난", "기록", "이력", "시연", "일정")
