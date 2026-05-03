from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel
from fastapi import WebSocket

from app.domain.gateway.gateway_sessions.session_service import SessionService


async def handle_subscription(
    websocket: WebSocket,
    *,
    session_service: SessionService,
    session_id: str,
    authenticated_user_id: str,
    task_run_id: str,
    last_sequence: int | None = None,
    request_id: str | None = None,
    send_json=None,
) -> None:
    """웹소켓 구독 처리와 세션 기록을 분리한다."""

    async def _send(message: dict) -> None:
        if send_json is not None:
            await send_json(message)
            return
        await websocket.send_json(message)

    projection_store = getattr(websocket.app.state, "task_projection_store", None)
    task = None
    if projection_store is not None:
        task = projection_store.get_task_snapshot(task_run_id)

    if task is None:
        repository = getattr(websocket.app.state, "repository", None)
        if repository is not None:
            # Redis snapshot TTL 만료나 projection miss 때도 durable repository로 소유권을 확인한다.
            task = repository.get_task(task_run_id)

    if task is None:
        response = {"type": "subscription.denied", "taskRunId": task_run_id, "reason": "not_found"}
        if request_id is not None:
            response["requestId"] = request_id
        await _send(response)
        return

    if str(task.owner_key) != str(authenticated_user_id):
        response = {"type": "subscription.denied", "taskRunId": task_run_id, "reason": "forbidden"}
        if request_id is not None:
            response["requestId"] = request_id
        await _send(response)
        return

    session_service.subscribe_task(session_id=session_id, websocket=websocket, task_run_id=task_run_id)
    response = {"type": "subscribed", "taskRunId": task_run_id}
    if request_id is not None:
        response["requestId"] = request_id
    if projection_store is not None:
        latest_sequence = projection_store.get_latest_sequence(task_run_id)
        if latest_sequence is not None:
            # 구독 ack의 최신 sequence는 client가 HTTP resync 필요 여부를 판단하는 힌트다.
            response["latestSequence"] = latest_sequence
    await _send(response)

    if last_sequence is None:
        return

    replay_events, retention_exceeded = _events_after_sequence(
        websocket=websocket,
        task_run_id=task_run_id,
        after_sequence=last_sequence,
    )
    if not replay_events:
        return
    # 재구독 직후 놓친 구간을 서버가 먼저 밀어 주면 client가 별도 command timeout에 걸릴 확률이 줄어든다.
    await _send(
        {
            "protocolVersion": 1,
            "type": "taskRun.events.replay.result",
            "payload": {
                "task_run_id": task_run_id,
                "events": replay_events,
                "latest_sequence": max(int(event.get("sequence") or 0) for event in replay_events),
                "retention_exceeded": retention_exceeded,
            },
        }
    )


def _events_after_sequence(*, websocket: WebSocket, task_run_id: str, after_sequence: int) -> tuple[list[dict[str, Any]], bool]:
    projection_store = getattr(websocket.app.state, "task_projection_store", None)
    if projection_store is not None:
        events = [
            event
            for event in projection_store.list_recent_events(task_run_id)
            if int(event.get("sequence") or 0) > after_sequence
        ]
        latest_sequence = projection_store.get_latest_sequence(task_run_id)
        min_returned_sequence = min((int(event.get("sequence") or 0) for event in events), default=None)
        retention_exceeded = bool(
            latest_sequence is not None
            and latest_sequence > after_sequence
            and (not events or (min_returned_sequence is not None and min_returned_sequence > after_sequence + 1))
        )
        if events and not retention_exceeded:
            return [_jsonable(event) for event in events], False

    repository = getattr(websocket.app.state, "repository", None)
    if repository is None:
        return [_jsonable(event) for event in events], retention_exceeded
    durable_events = [
        _jsonable(event)
        for event in repository.list_events(task_run_id)
        if int(getattr(event, "sequence", 0) or 0) > after_sequence
    ]
    if durable_events:
        return durable_events, retention_exceeded
    return [_jsonable(event) for event in events], retention_exceeded


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=False)
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value
