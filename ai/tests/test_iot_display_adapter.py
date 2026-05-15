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
    assert payload.text == "입력 기다리는 중"
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
    assert payload.text == "날씨 확인중"
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


async def test_mattermost_tool_started_uses_sending_message_text_key() -> None:
    client = RecordingIotDisplayClient()
    adapter = IotDisplayEventAdapter(client)

    await adapter.publish(
        event_type="tool.started",
        task=task_run(),
        step=step_run(),
        status="RUNNING",
        summary_message="메타모스트 전송 중",
        payload={"tool_name": "mattermost.send"},
    )

    payload = client.payloads[0]
    assert payload.type == "STEP"
    assert payload.icon == "SEND"
    assert payload.text == "메시지 전송중"
    assert payload.text_key == "SENDING_MESSAGE"


async def test_tool_completed_clears_tool_running_with_step_done() -> None:
    client = RecordingIotDisplayClient()
    adapter = IotDisplayEventAdapter(client)

    await adapter.publish(
        event_type="tool.completed",
        task=task_run(),
        step=step_run(),
        status="RUNNING",
        summary_message="전송 완료",
        payload={"tool_name": "mattermost.send"},
    )

    payload = client.payloads[0]
    assert payload.type == "STEP"
    assert payload.icon == "SUCCESS"
    assert payload.text == "전송 완료"
    assert payload.text_key == "STEP_DONE"


async def test_task_completed_publishes_terminal_done_payload() -> None:
    client = RecordingIotDisplayClient()
    adapter = IotDisplayEventAdapter(client)

    await adapter.publish(
        event_type="task.completed",
        task=task_run(status="COMPLETED"),
        step=step_run(status="COMPLETED"),
        status="COMPLETED",
        summary_message="작업 완료",
        payload={},
    )

    payload = client.payloads[0]
    assert payload.type == "DONE"
    assert payload.icon == "SUCCESS"
    assert payload.text == "답변 완료"
    assert payload.text_key == "DONE_SUCCESS"
    assert payload.focus is True


async def test_step_started_uses_korean_semantic_text() -> None:
    client = RecordingIotDisplayClient()
    adapter = IotDisplayEventAdapter(client)

    await adapter.publish(
        event_type="step.started",
        task=task_run(),
        step=step_run(detail_json={"semanticDetail": {"semanticKey": "response.compose"}}),
        status="RUNNING",
        summary_message="답변 작성",
        payload={},
    )

    payload = client.payloads[0]
    assert payload.type == "STEP"
    assert payload.icon == "WRITE"
    assert payload.text == "답변 작성중"
    assert payload.text_key == "WRITING_REPLY"


async def test_approval_waiting_uses_approval_text_key() -> None:
    client = RecordingIotDisplayClient()
    adapter = IotDisplayEventAdapter(client)

    await adapter.publish(
        event_type="step.waiting",
        task=task_run(wait_payload={"approval_id": "approval_1", "pending_tool_name": "terminal.run"}),
        step=step_run(status="WAITING"),
        status="WAITING",
        summary_message="승인 대기",
        payload={"approvalDetail": {"approvalRequested": True}},
    )

    payload = client.payloads[0]
    assert payload.type == "WAITING"
    assert payload.text == "승인 기다리는 중"
    assert payload.text_key == "WAITING_APPROVAL"


async def test_long_dynamic_korean_text_is_limited_for_oled() -> None:
    client = RecordingIotDisplayClient()
    adapter = IotDisplayEventAdapter(client)

    await adapter.publish(
        event_type="step.started",
        task=task_run(title="매우 긴 사용자 요청을 처리하는 중"),
        step=step_run(detail_json={"semanticDetail": {"semanticKey": "custom.long", "semanticStep": "사용자 요청을 아주 길게 분석하는 중입니다"}}),
        status="RUNNING",
        summary_message=None,
        payload={},
    )

    payload = client.payloads[0]
    assert payload.text == "사용자 요청을 아주 길"
    assert len(payload.text) <= 12
