from __future__ import annotations

from pydantic import BaseModel, Field

from app.contracts.event.task_events import TaskEventEnvelope


class WebSocketEvent(BaseModel):
    type: str = Field(
        default="task.event",
        description=(
            "WebSocket 메시지 종류입니다. 실시간 진행 이벤트는 `task.event`입니다. "
            "클라이언트 흐름은 `/realtime/user/ws` 연결 -> `auth.start` 전송 -> `auth.ok` 수신 -> `subscribe.task` 전송 -> `task.event` 수신입니다."
        ),
    )
    data: TaskEventEnvelope = Field(
        description="TaskRun event(시간순 진행 기록) 본문입니다. `sequence`는 재연결 후 `/taskRuns/{taskRunId}/events?afterSequence=` 복구에 사용합니다."
    )
