from __future__ import annotations

from pydantic import BaseModel

from app.contracts.event.task_events import TaskEventEnvelope


class WebSocketEvent(BaseModel):
    type: str = "task.event"
    data: TaskEventEnvelope
