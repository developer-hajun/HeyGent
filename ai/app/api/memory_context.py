from __future__ import annotations

import logging
from typing import Any

from app.clients.backend_memory import BackendMemoryClientError
from app.domain.orchestration.prompts.persistent_memory_prompt import build_persistent_memory_prompt

logger = logging.getLogger(__name__)

DEFAULT_MEMORY_RECALL_LIMIT = 5
MEMORY_CONTEXT_KEYS = ("persistent_memory_context", "memory_context")
MEMORY_RECALL_QUERY_KEYS = ("prompt", "message", "query", "content", "text", "subject", "title")


def clear_client_memory_context(task_input: dict[str, Any]) -> None:
    for key in MEMORY_CONTEXT_KEYS:
        task_input.pop(key, None)


def select_memory_recall_query(input_payload: dict[str, Any]) -> str | None:
    for key in MEMORY_RECALL_QUERY_KEYS:
        value = input_payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


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
    normalized_query = str(query or "").strip()
    if not normalized_query:
        return

    memory_client = getattr(app_state, "backend_memory_client", None)
    if memory_client is None:
        return

    try:
        memories = await memory_client.recall(
            user_id=str(user_id),
            query=normalized_query,
            limit=limit,
            workspace_key=workspace_key,
        )
    except BackendMemoryClientError:
        logger.warning("backend memory recall failed; continuing without persistent memory context", exc_info=True)
        return

    memory_prompt = build_persistent_memory_prompt(memories)
    if memory_prompt:
        task_input["persistent_memory_context"] = memory_prompt
