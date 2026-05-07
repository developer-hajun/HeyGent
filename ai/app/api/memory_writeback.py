from __future__ import annotations

import logging
from typing import Any

from app.clients.backend_memory import BackendMemoryClientError
from app.domain.orchestration.agent.memory.memory_extractor import MemoryExtractionContext


logger = logging.getLogger(__name__)


async def writeback_persistent_memory_candidates(
    *,
    app_state: Any,
    user_id: str,
    user_message: str,
    assistant_message: str,
    session_id: str,
    workspace_key: str | None = None,
    task_run_id: str | None = None,
    user_message_id: str | None = None,
    assistant_message_id: str | None = None,
) -> None:
    """대화 완료 후 장기기억 후보를 추출해 backend에 저장 요청한다.

    writeback은 부가 기능이므로 실패해도 대화 저장/응답 흐름을 깨지 않는다.
    """

    memory_client = getattr(app_state, "backend_memory_client", None)
    memory_extractor = getattr(app_state, "memory_extractor", None)
    if memory_client is None or memory_extractor is None:
        return

    context = MemoryExtractionContext(
        user_id=user_id,
        session_id=session_id,
        workspace_key=workspace_key,
        task_run_id=task_run_id,
        user_message_id=user_message_id,
        assistant_message_id=assistant_message_id,
    )
    try:
        candidates = await memory_extractor.extract_candidates(
            user_message=user_message,
            assistant_message=assistant_message,
            context=context,
        )
    except Exception:
        logger.warning("장기기억 후보 추출에 실패했습니다.", exc_info=True)
        return
    if not candidates:
        return

    try:
        await memory_client.create_candidates(user_id=user_id, candidates=candidates)
    except BackendMemoryClientError:
        logger.warning("backend 장기기억 후보 저장 요청에 실패했습니다.", exc_info=True)
    except Exception:
        logger.warning("장기기억 후보 저장 중 예기치 않은 예외가 발생했습니다.", exc_info=True)
