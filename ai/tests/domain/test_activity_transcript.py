from __future__ import annotations

from app.contracts.event.task_events import TaskEventEnvelope
from app.domain.tasks.activity_transcript import build_activity_transcript


def _event(
    event_id: str,
    event_type: str,
    *,
    sequence: int,
    step_run_id: str | None = None,
    payload: dict | None = None,
    summary_message: str | None = None,
    status: str | None = None,
) -> TaskEventEnvelope:
    return TaskEventEnvelope(
        event_id=event_id,
        event_type=event_type,
        task_run_id="task-1",
        step_run_id=step_run_id,
        producer="test",
        occurred_at=f"2026-05-14T00:00:{sequence:02d}+00:00",
        status=status,
        summary_message=summary_message,
        payload=payload or {},
        sequence=sequence,
    )


def test_activity_transcript_pairs_tool_started_and_completed_by_call_id():
    activities = build_activity_transcript(
        [
            _event(
                "event-tool-start",
                "tool.started",
                sequence=1,
                step_run_id="step-1",
                payload={"tool_call_id": "call-weather", "tool_name": "http_get", "title": "날씨 조회"},
            ),
            _event(
                "event-tool-complete",
                "tool.completed",
                sequence=2,
                step_run_id="step-1",
                payload={
                    "tool_call_id": "call-weather",
                    "tool_name": "http_get",
                    "title": "날씨 조회 완료",
                    "result": {"ok": True},
                },
            ),
        ]
    )

    assert len(activities) == 1
    assert activities[0]["activity_id"] == "tool:task-1:call-weather"
    assert activities[0]["status"] == "COMPLETED"
    assert activities[0]["started_event_id"] == "event-tool-start"
    assert activities[0]["completed_event_id"] == "event-tool-complete"
    assert activities[0]["tool_call_id"] == "call-weather"
    assert activities[0]["tool_name"] == "http_get"


def test_activity_transcript_keeps_step_titles_as_stable_step_items():
    activities = build_activity_transcript(
        [
            _event(
                "event-step-created",
                "step.created",
                sequence=1,
                step_run_id="step-1",
                payload={"step_title": "날씨 API 조회"},
                summary_message="날씨 API 조회",
            ),
            _event(
                "event-step-complete",
                "step.completed",
                sequence=4,
                step_run_id="step-1",
                payload={"step_title": "날씨 API 조회"},
                summary_message="날씨 API 조회 완료",
            ),
        ]
    )

    assert len(activities) == 1
    assert activities[0]["activity_id"] == "step:task-1:step-1"
    assert activities[0]["kind"] == "step"
    assert activities[0]["title"] == "날씨 API 조회"
    assert activities[0]["status"] == "COMPLETED"
    assert activities[0]["first_sequence"] == 1
    assert activities[0]["last_sequence"] == 4

