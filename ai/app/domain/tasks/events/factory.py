from __future__ import annotations

from typing import Any

from app.contracts.event.task_events import TaskEventEnvelope
from app.core.time import utc_now
from app.core.utils.ids import new_id


def build_task_event(
    *,
    event_type: str,
    task_run_id: str,
    producer: str,
    step_run_id: str | None = None,
    status: str | None = None,
    summary_message: str | None = None,
    payload: dict[str, Any] | None = None,
) -> TaskEventEnvelope:
    """저장과 브로드캐스트에서 동일한 envelope 를 재사용한다."""

    return TaskEventEnvelope(
        event_id=new_id("evt"),
        event_type=event_type,
        task_run_id=task_run_id,
        step_run_id=step_run_id,
        producer=producer,
        occurred_at=utc_now().isoformat(),
        status=status,
        summary_message=summary_message,
        payload=payload or {},
    )
