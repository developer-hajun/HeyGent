from __future__ import annotations

from typing import Any


def build_activity_transcript(events: list[Any]) -> list[dict[str, Any]]:
    activities: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for event in _sorted_events(events):
        event_type = str(_get(event, "event_type") or "")
        if event_type.startswith("tool."):
            activity_id = _tool_activity_id(event)
            if not activity_id:
                continue
            activity = activities.get(activity_id)
            if activity is None:
                activity = _base_tool_activity(event, activity_id=activity_id)
                activities[activity_id] = activity
                order.append(activity_id)
            _merge_tool_event(activity, event)
            continue
        if event_type.startswith("step."):
            activity_id = _step_activity_id(event)
            if not activity_id:
                continue
            activity = activities.get(activity_id)
            if activity is None:
                activity = _base_step_activity(event, activity_id=activity_id)
                activities[activity_id] = activity
                order.append(activity_id)
            _merge_step_event(activity, event)
    return [activities[activity_id] for activity_id in order]


def _base_tool_activity(event: Any, *, activity_id: str) -> dict[str, Any]:
    payload = _payload(event)
    return {
        "activity_id": activity_id,
        "activityId": activity_id,
        "task_run_id": _get(event, "task_run_id"),
        "taskRunId": _get(event, "task_run_id"),
        "step_run_id": _get(event, "step_run_id"),
        "stepRunId": _get(event, "step_run_id"),
        "kind": "tool",
        "tool_call_id": payload.get("tool_call_id") or payload.get("toolCallId"),
        "toolCallId": payload.get("tool_call_id") or payload.get("toolCallId"),
        "tool_name": payload.get("tool_name") or payload.get("toolName"),
        "toolName": payload.get("tool_name") or payload.get("toolName"),
        "title": _event_title(event),
        "status": "RUNNING",
        "first_sequence": _get(event, "sequence"),
        "firstSequence": _get(event, "sequence"),
        "last_sequence": _get(event, "sequence"),
        "lastSequence": _get(event, "sequence"),
        "started_event_id": None,
        "startedEventId": None,
        "completed_event_id": None,
        "completedEventId": None,
        "occurred_at": _get(event, "occurred_at"),
        "occurredAt": _get(event, "occurred_at"),
        "payload": payload,
    }


def _base_step_activity(event: Any, *, activity_id: str) -> dict[str, Any]:
    return {
        "activity_id": activity_id,
        "activityId": activity_id,
        "task_run_id": _get(event, "task_run_id"),
        "taskRunId": _get(event, "task_run_id"),
        "step_run_id": _get(event, "step_run_id"),
        "stepRunId": _get(event, "step_run_id"),
        "kind": "step",
        "title": _event_title(event),
        "status": _step_status(_get(event, "event_type")),
        "first_sequence": _get(event, "sequence"),
        "firstSequence": _get(event, "sequence"),
        "last_sequence": _get(event, "sequence"),
        "lastSequence": _get(event, "sequence"),
        "started_event_id": None,
        "startedEventId": None,
        "completed_event_id": None,
        "completedEventId": None,
        "occurred_at": _get(event, "occurred_at"),
        "occurredAt": _get(event, "occurred_at"),
        "payload": _payload(event),
    }


def _merge_tool_event(activity: dict[str, Any], event: Any) -> None:
    event_type = str(_get(event, "event_type") or "")
    payload = _payload(event)
    if event_type == "tool.started":
        activity["started_event_id"] = _get(event, "event_id")
        activity["startedEventId"] = _get(event, "event_id")
        activity["status"] = "RUNNING"
    elif event_type == "tool.completed":
        activity["completed_event_id"] = _get(event, "event_id")
        activity["completedEventId"] = _get(event, "event_id")
        result = payload.get("result")
        activity["status"] = "FAILED" if isinstance(result, dict) and result.get("ok") is False else "COMPLETED"
    _merge_common(activity, event)


def _merge_step_event(activity: dict[str, Any], event: Any) -> None:
    event_type = str(_get(event, "event_type") or "")
    if event_type in {"step.started", "step.created"}:
        activity["started_event_id"] = activity.get("started_event_id") or _get(event, "event_id")
        activity["startedEventId"] = activity.get("started_event_id")
    if event_type in {"step.completed", "step.failed", "step.canceled"}:
        activity["completed_event_id"] = _get(event, "event_id")
        activity["completedEventId"] = _get(event, "event_id")
    activity["status"] = _step_status(event_type)
    _merge_common(activity, event)


def _merge_common(activity: dict[str, Any], event: Any) -> None:
    sequence = _get(event, "sequence")
    activity["last_sequence"] = sequence
    activity["lastSequence"] = sequence
    activity["occurred_at"] = _get(event, "occurred_at")
    activity["occurredAt"] = _get(event, "occurred_at")
    activity["payload"] = _payload(event)
    if not activity.get("title"):
        activity["title"] = _event_title(event)


def _tool_activity_id(event: Any) -> str | None:
    payload = _payload(event)
    tool_call_id = str(payload.get("tool_call_id") or payload.get("toolCallId") or "").strip()
    task_run_id = str(_get(event, "task_run_id") or "").strip()
    return f"tool:{task_run_id}:{tool_call_id}" if task_run_id and tool_call_id else None


def _step_activity_id(event: Any) -> str | None:
    step_run_id = str(_get(event, "step_run_id") or "").strip()
    task_run_id = str(_get(event, "task_run_id") or "").strip()
    return f"step:{task_run_id}:{step_run_id}" if task_run_id and step_run_id else None


def _event_title(event: Any) -> str:
    payload = _payload(event)
    for key in ("step_title", "stepTitle", "title"):
        value = str(payload.get(key) or "").strip()
        if value:
            return value
    summary = str(_get(event, "summary_message") or "").strip()
    if summary:
        return summary
    return str(payload.get("tool_name") or payload.get("toolName") or _get(event, "event_type") or "")


def _step_status(event_type: Any) -> str:
    if event_type == "step.completed":
        return "COMPLETED"
    if event_type in {"step.failed", "step.canceled"}:
        return "FAILED"
    return "RUNNING"


def _sorted_events(events: list[Any]) -> list[Any]:
    return sorted(events, key=lambda event: int(_get(event, "sequence") or 0))


def _payload(event: Any) -> dict[str, Any]:
    payload = _get(event, "payload")
    return dict(payload) if isinstance(payload, dict) else {}


def _get(event: Any, key: str) -> Any:
    if isinstance(event, dict):
        return event.get(key)
    return getattr(event, key, None)

