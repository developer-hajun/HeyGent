from __future__ import annotations

from fastapi import WebSocket

from app.domain.gateway.gateway_sessions.session_service import SessionService


async def handle_subscription(
    websocket: WebSocket,
    *,
    session_service: SessionService,
    session_id: str,
    authenticated_user_id: str,
    task_run_id: str,
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
