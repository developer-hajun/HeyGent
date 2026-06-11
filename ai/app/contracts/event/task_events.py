from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskEventEnvelope(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event_id: str = Field(description="event ID(시간순 진행 기록 ID)입니다.")
    event_id_alias: str | None = Field(default=None, alias="eventId", description="event_id와 같은 값의 camelCase 별칭입니다.")
    event_type: str = Field(description="event 종류입니다. 예: `task.created`, `step.started`, `task.completed`.")
    task_run_id: str = Field(description="event가 속한 TaskRun(사용자 요청 실행 묶음) ID입니다.")
    step_run_id: str | None = Field(default=None, description="특정 StepRun(세부 단계)에서 발생한 event이면 StepRun ID가 들어갑니다.")
    producer: str = Field(description="event를 만든 내부 구성요소 이름입니다. 예: `orchestrator`, `task-engine`.")
    occurred_at: str = Field(description="event가 발생한 시각입니다.")
    status: str | None = Field(default=None, description="event 발생 시점의 상태입니다.")
    summary_message: str | None = Field(default=None, description="화면 로그에 보여 줄 수 있는 진행 요약입니다.")
    payload: dict[str, Any] = Field(default_factory=dict, description="event별 추가 데이터입니다. UI가 모르는 키는 무시해도 됩니다.")
    sequence: int | None = Field(default=None, description="TaskRun 안에서 증가하는 순번입니다. 재연결 후 빠진 event를 복구할 때 사용합니다.")
