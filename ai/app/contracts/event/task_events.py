from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskEventEnvelope(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event_id: str
    event_id_alias: str | None = Field(default=None, alias="eventId")
    event_type: str
    task_run_id: str
    step_run_id: str | None = None
    producer: str
    occurred_at: str
    status: str | None = None
    summary_message: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    sequence: int | None = None
