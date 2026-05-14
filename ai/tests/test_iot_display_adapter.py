from __future__ import annotations

from app.domain.orchestration.agent.iot_display import IotDisplayEventAdapter
from app.domain.tasks.models import StepRun, TaskRun


class RecordingIotDisplayClient:
    enabled = True

    def __init__(self) -> None:
        self.payloads = []

    async def publish(self, payload) -> None:
        self.payloads.append(payload)


def task_run(**kwargs) -> TaskRun:
    defaults = {
        "task_run_id": "task_1",
        "task_type": "agent.loop",
        "owner_key": "7",
        "status": "RUNNING",
        "session_key": "session_1",
        "title": "날씨 확인",
        "input_payload": {},
    }
    defaults.update(kwargs)
    return TaskRun(**defaults)


def step_run(**kwargs) -> StepRun:
    defaults = {
        "step_run_id": "step_1",
        "task_run_id": "task_1",
        "step_order": 1,
        "step_type": "agent.loop.execute",
        "status": "RUNNING",
        "title": "HTTP 호출 중",
        "detail_json": {"semanticDetail": {"semanticKey": "search"}},
    }
    defaults.update(kwargs)
    return StepRun(**defaults)


async def test_waiting_event_becomes_focused_device_payload() -> None:
    client = RecordingIotDisplayClient()
    adapter = IotDisplayEventAdapter(client)

    await adapter.publish(
        event_type="step.waiting",
        task=task_run(status="WAITING"),
        step=step_run(status="WAITING"),
        status="WAITING",
        summary_message="사용자 입력 대기",
        payload={},
    )

    payload = client.payloads[0]
    assert payload.user_id == 7
    assert payload.session_id == "session_1"
    assert payload.type == "WAITING"
    assert payload.icon == "QUESTION"
    assert payload.text_key == "WAITING_INPUT"
    assert payload.ttl_ms == 0
    assert payload.focus is True


async def test_started_event_uses_device_start_signal() -> None:
    client = RecordingIotDisplayClient()
    adapter = IotDisplayEventAdapter(client)

    await adapter.publish(
        event_type="task.started",
        task=task_run(),
        step=None,
        status="RUNNING",
        summary_message="요청 확인중",
        payload={},
    )

    payload = client.payloads[0]
    assert payload.type == "STARTED"
    assert payload.icon == "START"
    assert payload.text_key == "CHECKING_REQUEST"
    assert payload.priority == 80
    assert payload.focus is True


async def test_non_numeric_owner_is_skipped() -> None:
    client = RecordingIotDisplayClient()
    adapter = IotDisplayEventAdapter(client)

    await adapter.publish(
        event_type="task.started",
        task=task_run(owner_key="local-user"),
        step=None,
        status="RUNNING",
        summary_message="요청 확인중",
        payload={},
    )

    assert client.payloads == []
