from __future__ import annotations

from dataclasses import dataclass, field
import math
import sys
from typing import Any, Callable
from urllib.parse import urlencode

from app.cli.core.transport import request_path
from app.cli.ui.output import render_plain_box
from app.core.config import Settings

InputFunc = Callable[[str], str]
OutputFunc = Callable[[str], None]

# v1 에서는 자주 쓰는 필터만 먼저 노출한다.
# 전체/진행중/대기/완료 정도만 있어도 작업 브라우저 체감이 크게 좋아진다.
TASK_BROWSER_FILTERS: dict[str, str] = {
    "ALL": "전체",
    "RUNNING": "진행중",
    "WAITING": "대기",
    "COMPLETED": "완료",
}

FILTER_ALIASES: dict[str, str] = {
    "all": "ALL",
    "전체": "ALL",
    "running": "RUNNING",
    "run": "RUNNING",
    "진행중": "RUNNING",
    "waiting": "WAITING",
    "wait": "WAITING",
    "대기": "WAITING",
    "completed": "COMPLETED",
    "complete": "COMPLETED",
    "done": "COMPLETED",
    "완료": "COMPLETED",
}


@dataclass(slots=True)
class TaskBrowserState:
    status_filter: str = "ALL"
    page: int = 1
    page_size: int = 8
    selected_index: int = 0
    depth: str = "list"
    list_payload: dict[str, Any] = field(default_factory=dict)
    detail_task: dict[str, Any] | None = None
    detail_steps: list[dict[str, Any]] = field(default_factory=list)
    detail_events: list[dict[str, Any]] = field(default_factory=list)
    selected_task_id: str | None = None


class TaskBrowserRequestError(RuntimeError):
    pass


def normalize_browser_filter(raw_value: str | None) -> str:
    if raw_value is None:
        return "ALL"
    normalized = FILTER_ALIASES.get(raw_value.strip().lower())
    return normalized or raw_value.strip().upper()


def build_tasks_list_path(settings: Settings, *, status_filter: str, page: int, page_size: int) -> str:
    query = urlencode({"status": status_filter, "page": page, "page_size": page_size})
    return request_path(settings, f"/tasks?{query}")


def _raise_request_error(response, payload: Any, *, action: str) -> None:
    """브라우저 요청 실패를 사용자 입장에서 이해하기 쉬운 문장으로 바꾼다."""

    status_code = getattr(response, "status_code", None)
    detail = payload.get("detail") if isinstance(payload, dict) else None

    if action == "list" and status_code == 405:
        raise TaskBrowserRequestError("현재 실행 중인 서버가 아직 GET /tasks 를 지원하지 않아. 최신 코드 반영 후 서버를 재시작해 줘.")
    if action == "detail" and status_code == 404:
        raise TaskBrowserRequestError("선택한 task 를 서버에서 찾지 못했어. 이미 정리됐거나 다른 DB 를 보고 있을 수 있어.")
    if detail:
        raise TaskBrowserRequestError(str(detail))
    raise TaskBrowserRequestError(str(payload))


def fetch_tasks_page(client, settings: Settings, *, status_filter: str, page: int, page_size: int) -> dict[str, Any]:
    response = client.request("GET", build_tasks_list_path(settings, status_filter=status_filter, page=page, page_size=page_size))
    payload = response.json()
    if not response.is_success:
        _raise_request_error(response, payload, action="list")
    return payload


def fetch_task_detail_bundle(client, settings: Settings, task_run_id: str) -> dict[str, Any]:
    task_response = client.request("GET", request_path(settings, f"/tasks/{task_run_id}"))
    steps_response = client.request("GET", request_path(settings, f"/tasks/{task_run_id}/steps"))
    events_response = client.request("GET", request_path(settings, f"/tasks/{task_run_id}/events"))

    task_payload = task_response.json()
    steps_payload = steps_response.json()
    events_payload = events_response.json()
    if not task_response.is_success:
        _raise_request_error(task_response, task_payload, action="detail")
    if not steps_response.is_success:
        _raise_request_error(steps_response, steps_payload, action="detail")
    if not events_response.is_success:
        _raise_request_error(events_response, events_payload, action="detail")
    return {"task": task_payload, "steps": steps_payload, "events": events_payload}


def _clamp_selected_index(state: TaskBrowserState) -> None:
    items = state.list_payload.get("items") or []
    if not items:
        state.selected_index = 0
        return
    state.selected_index = max(0, min(state.selected_index, len(items) - 1))


def _selected_item(state: TaskBrowserState) -> dict[str, Any] | None:
    items = state.list_payload.get("items") or []
    if not items:
        return None
    _clamp_selected_index(state)
    return items[state.selected_index]


def _select_current_step(steps: list[dict[str, Any]]) -> dict[str, Any] | None:
    for step in steps:
        if step.get("status") in {"PENDING", "RUNNING", "WAITING", "BLOCKED"}:
            return step
    return steps[-1] if steps else None


def _format_time(raw_value: str | None) -> str:
    if not raw_value:
        return "-"
    return raw_value.replace("T", " ").split("+")[0]


def _step_summary(item: dict[str, Any]) -> str:
    current_step = item.get("current_step") or {}
    return str(current_step.get("summary_message") or current_step.get("title") or item.get("progress_summary") or "-")


def _render_filter_tabs(selected_filter: str) -> str:
    segments: list[str] = []
    for code, label in TASK_BROWSER_FILTERS.items():
        segments.append(f"[{label}]" if code == selected_filter else label)
    return " / ".join(segments)


def render_tasks_browser_list(state: TaskBrowserState) -> str:
    payload = state.list_payload or {}
    items = payload.get("items") or []
    total_count = int(payload.get("total_count") or 0)
    page = int(payload.get("page") or 1)
    page_size = int(payload.get("page_size") or max(1, state.page_size))
    total_pages = max(1, math.ceil(total_count / page_size)) if total_count else 1

    lines = [
        "Tasks",
        f"필터: {_render_filter_tabs(state.status_filter)}",
        f"페이지: {page}/{total_pages}   총 {total_count}개",
        "",
    ]

    if not items:
        lines.append("표시할 작업이 없습니다.")
    else:
        for index, item in enumerate(items, start=1):
            selected = index - 1 == state.selected_index
            marker = "›" if selected else " "
            title = str(item.get("title") or item.get("task_type") or item.get("task_run_id"))
            status = str(item.get("status") or "-")
            step_summary = _step_summary(item)
            task_id = str(item.get("task_run_id") or "-")
            updated_at = _format_time(item.get("updated_at") or item.get("created_at"))
            lines.append(f"{marker} [{index}] {title} | {status} | {step_summary}")
            lines.append(f"    id: {task_id} • updated: {updated_at}")

    lines.extend(
        [
            "",
            "<이전> <다음> <열기> <돌아가기>",
            "명령: 번호 입력 / j,k 이동 / all,running,waiting,completed 필터 / <,> 페이지 / b 종료",
        ]
    )
    return render_plain_box(lines)


def _render_step_detail_lines(step: dict[str, Any]) -> list[str]:
    detail = step.get("detail_json") or {}
    agent_detail = detail.get("agentDetail") or {}
    tool_detail = detail.get("toolDetail") or {}
    llm_detail = detail.get("llmDetail") or {}

    tool_names = ", ".join(tool_detail.get("toolNames") or []) or "-"
    agent_called = "yes" if agent_detail.get("called") else "no"
    llm_model = llm_detail.get("model") or "-"
    llm_calls = llm_detail.get("callCount") or 0
    return [
        f"- agent: {agent_called}",
        f"- tool: {tool_names}",
        f"- llm: {llm_model} ({llm_calls}회)",
    ]


def render_tasks_browser_detail(state: TaskBrowserState) -> str:
    task = state.detail_task or {}
    steps = state.detail_steps or []
    events = state.detail_events or []
    current_step = _select_current_step(steps)
    title = str(task.get("title") or task.get("task_type") or task.get("task_run_id") or "-")

    lines = [
        f"Tasks > {title}",
        f"상태: {task.get('status') or '-'}",
        f"flow: {task.get('flow_name') or '-'}",
        f"업데이트: {_format_time(task.get('updated_at') or task.get('created_at'))}",
    ]

    if current_step is not None:
        lines.extend(
            [
                "",
                "현재 Step",
                f"- {current_step.get('title') or current_step.get('step_type') or '-'} | {current_step.get('status') or '-'}",
            ]
        )
        summary = current_step.get("summary_message")
        if summary:
            lines.append(f"- 요약: {summary}")
        lines.extend(_render_step_detail_lines(current_step))

    lines.extend(["", "Step 목록"])
    if not steps:
        lines.append("- step 없음")
    else:
        current_step_id = current_step.get("step_run_id") if current_step else None
        for step in steps:
            marker = "›" if step.get("step_run_id") == current_step_id else "-"
            summary = step.get("summary_message") or step.get("title") or step.get("step_type") or "-"
            lines.append(f"{marker} #{step.get('step_order')} {summary} | {step.get('status') or '-'}")

    lines.extend(["", "최근 Event"])
    recent_events = events[-5:]
    if not recent_events:
        lines.append("- event 없음")
    else:
        for event in recent_events:
            event_summary = event.get("summary_message") or event.get("status") or "-"
            lines.append(f"- {event.get('event_type') or '-'} | {event_summary}")

    lines.extend(["", "<돌아가기>", "명령: b"])
    return render_plain_box(lines)


def _clear_terminal() -> None:
    if sys.stdout.isatty():
        print("\033[2J\033[H", end="")
    else:
        print()


def _load_list(client, settings: Settings, state: TaskBrowserState) -> None:
    state.list_payload = fetch_tasks_page(client, settings, status_filter=state.status_filter, page=state.page, page_size=state.page_size)
    _clamp_selected_index(state)


def _load_detail(client, settings: Settings, state: TaskBrowserState, task_run_id: str) -> None:
    bundle = fetch_task_detail_bundle(client, settings, task_run_id)
    state.detail_task = bundle["task"]
    state.detail_steps = bundle["steps"]
    state.detail_events = bundle["events"]
    state.selected_task_id = task_run_id
    state.depth = "detail"


def _update_filter(state: TaskBrowserState, next_filter: str) -> None:
    state.status_filter = next_filter
    state.page = 1
    state.selected_index = 0
    state.depth = "list"


def run_tasks_browser(
    client,
    settings: Settings,
    *,
    initial_filter: str = "ALL",
    initial_task_id: str | None = None,
    input_func: InputFunc = input,
    output_func: OutputFunc = print,
) -> None:
    state = TaskBrowserState(status_filter=normalize_browser_filter(initial_filter))

    try:
        _load_list(client, settings, state)
        if initial_task_id:
            _load_detail(client, settings, state, initial_task_id)
    except TaskBrowserRequestError as error:
        output_func(f"작업 브라우저를 열지 못했어: {error}")
        return

    while True:
        _clear_terminal()
        output_func(render_tasks_browser_detail(state) if state.depth == "detail" else render_tasks_browser_list(state))
        try:
            raw_command = input_func("tasks> ").strip()
        except (EOFError, KeyboardInterrupt):
            output_func("작업 브라우저를 닫을게.")
            return

        command = raw_command.lower()
        if state.depth == "detail":
            if command in {"b", "back", "돌아가기", "q", "quit", "exit"}:
                state.depth = "list"
                continue
            continue

        if command in {"b", "back", "돌아가기", "q", "quit", "exit"}:
            output_func("작업 브라우저를 닫을게.")
            return
        if command in {"j", "down"}:
            state.selected_index += 1
            _clamp_selected_index(state)
            continue
        if command in {"k", "up"}:
            state.selected_index -= 1
            _clamp_selected_index(state)
            continue
        if command in {"<", "p", "prev", "이전"}:
            if state.list_payload.get("has_previous"):
                state.page = max(1, state.page - 1)
                state.selected_index = 0
                _load_list(client, settings, state)
            continue
        if command in {">", "n", "next", "다음"}:
            if state.list_payload.get("has_next"):
                state.page += 1
                state.selected_index = 0
                _load_list(client, settings, state)
            continue
        if command in {alias.lower() for alias in FILTER_ALIASES}:
            normalized_filter = normalize_browser_filter(raw_command)
            if normalized_filter in TASK_BROWSER_FILTERS:
                _update_filter(state, normalized_filter)
                _load_list(client, settings, state)
            continue
        if command in {"", "o", "open", "열기"}:
            selected_item = _selected_item(state)
            if selected_item is not None:
                _load_detail(client, settings, state, str(selected_item.get("task_run_id")))
            continue
        if raw_command.isdigit():
            target_index = int(raw_command) - 1
            items = state.list_payload.get("items") or []
            if 0 <= target_index < len(items):
                state.selected_index = target_index
                _load_detail(client, settings, state, str(items[target_index].get("task_run_id")))
            continue
