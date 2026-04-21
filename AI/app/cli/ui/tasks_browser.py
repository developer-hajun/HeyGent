from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
import os
import sys
from typing import Any, Callable
from urllib.parse import urlencode

try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None  # type: ignore[assignment]

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

_ACTIVE_STEP_STATUSES = {"PENDING", "RUNNING", "WAITING", "BLOCKED"}
_ANSI_RESET = "\033[0m"
_ANSI_SELECTED = "\033[97m"
_ANSI_MUTED = "\033[90m"
_ANSI_ACCENT = "\033[96m"


@dataclass(slots=True)
class TaskBrowserState:
    status_filter: str = "ALL"
    page: int = 1
    page_size: int = 8
    selected_index: int = 0
    selected_step_index: int = 0
    depth: str = "task_list"
    list_payload: dict[str, Any] = field(default_factory=dict)
    detail_task: dict[str, Any] | None = None
    detail_steps: list[dict[str, Any]] = field(default_factory=list)
    detail_events: list[dict[str, Any]] = field(default_factory=list)
    selected_task_id: str | None = None


class TaskBrowserRequestError(RuntimeError):
    pass


class TaskBrowserExit(Exception):
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



def _clamp_selected_step_index(state: TaskBrowserState) -> None:
    if not state.detail_steps:
        state.selected_step_index = 0
        return
    state.selected_step_index = max(0, min(state.selected_step_index, len(state.detail_steps) - 1))



def _selected_task_item(state: TaskBrowserState) -> dict[str, Any] | None:
    items = state.list_payload.get("items") or []
    if not items:
        return None
    _clamp_selected_index(state)
    return items[state.selected_index]



def _selected_step_item(state: TaskBrowserState) -> dict[str, Any] | None:
    if not state.detail_steps:
        return None
    _clamp_selected_step_index(state)
    return state.detail_steps[state.selected_step_index]



def _select_current_step(steps: list[dict[str, Any]]) -> dict[str, Any] | None:
    for step in steps:
        if step.get("status") in _ACTIVE_STEP_STATUSES:
            return step
    return steps[-1] if steps else None



def _format_time(raw_value: str | None) -> str:
    if not raw_value:
        return "-"
    return raw_value.replace("T", " ").replace("Z", "").split("+")[0]



def _truncate_text(value: str | None, *, limit: int = 64) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text or "-"
    return text[: limit - 1].rstrip() + "…"



def _task_input_summary(item: dict[str, Any]) -> str:
    return _truncate_text(item.get("input_summary") or item.get("progress_summary") or "입력 요약 없음", limit=56)



def _task_title(item: dict[str, Any]) -> str:
    return _truncate_text(item.get("title") or item.get("flow_name") or item.get("task_type") or item.get("task_run_id") or "-", limit=40)



def _current_step_summary(item: dict[str, Any]) -> str:
    current_step = item.get("current_step") or {}
    return _truncate_text(current_step.get("summary_message") or current_step.get("title") or item.get("progress_summary") or "-", limit=52)



def _style_line(text: str, *, selected: bool = False, muted: bool = False, accent: bool = False) -> str:
    if not sys.stdout.isatty():
        return text
    if selected:
        return f"{_ANSI_SELECTED}{text}{_ANSI_RESET}"
    if accent:
        return f"{_ANSI_ACCENT}{text}{_ANSI_RESET}"
    if muted:
        return f"{_ANSI_MUTED}{text}{_ANSI_RESET}"
    return text



def _render_filter_tabs(selected_filter: str) -> str:
    segments: list[str] = []
    for code, label in TASK_BROWSER_FILTERS.items():
        if code == selected_filter:
            segments.append(_style_line(f"[{label}]", accent=True))
        else:
            segments.append(label)
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
            title = _task_title(item)
            status = str(item.get("status") or "-")
            input_summary = _task_input_summary(item)
            step_count = int(item.get("step_count") or 0)
            current_step = _current_step_summary(item)
            task_id = str(item.get("task_run_id") or "-")
            updated_at = _format_time(item.get("updated_at") or item.get("created_at"))
            headline = f"{marker} [{index}] {title} | {status} | step {step_count}개"
            detail = f"    입력: {input_summary}"
            progress = f"    현재: {current_step}"
            meta = f"    id: {task_id} • updated: {updated_at}"
            lines.append(_style_line(headline, selected=selected))
            lines.append(_style_line(detail, selected=selected, muted=not selected))
            lines.append(_style_line(progress, selected=selected, muted=not selected))
            lines.append(_style_line(meta, selected=selected, muted=not selected))

    lines.extend(
        [
            "",
            "<이전> <다음> <열기> <돌아가기>",
            "명령: ↑↓ 이동 / ←→ 페이지 / Enter 열기 / Esc·Backspace 뒤로 / 번호·필터 직접 입력 가능",
        ]
    )
    return render_plain_box(lines)



def _task_detail_title(task: dict[str, Any]) -> str:
    return _truncate_text(task.get("title") or task.get("flow_name") or task.get("task_type") or task.get("task_run_id") or "-", limit=48)



def _task_detail_input_summary(task: dict[str, Any]) -> str:
    payload = task.get("input_payload") or {}
    preferred = [payload.get("prompt"), payload.get("message"), payload.get("subject"), payload.get("title"), payload.get("content")]
    for value in preferred:
        if isinstance(value, str) and value.strip():
            return _truncate_text(value, limit=72)
    if payload:
        return _truncate_text(str(payload), limit=72)
    return "입력 요약 없음"



def _render_task_detail(state: TaskBrowserState) -> str:
    task = state.detail_task or {}
    steps = state.detail_steps or []
    current_step = _select_current_step(steps)
    lines = [
        f"Tasks > {_task_detail_title(task)}",
        f"상태: {task.get('status') or '-'}",
        f"입력: {_task_detail_input_summary(task)}",
        f"step: {len(steps)}개   flow: {task.get('flow_name') or '-'}",
        f"최근 갱신: {_format_time(task.get('updated_at') or task.get('created_at'))}",
        "",
        "Step 목록",
    ]

    if not steps:
        lines.append("step 이 없습니다.")
    else:
        current_step_id = current_step.get("step_run_id") if current_step else None
        for index, step in enumerate(steps, start=1):
            selected = index - 1 == state.selected_step_index
            active = step.get("step_run_id") == current_step_id
            marker = "›" if selected else " "
            badge = "현재" if active else f"#{index}"
            title = _truncate_text(step.get("title") or step.get("step_type") or "-", limit=42)
            summary = _truncate_text(step.get("summary_message") or "요약 없음", limit=56)
            headline = f"{marker} [{badge}] {title} | {step.get('status') or '-'}"
            detail = f"    설명: {summary}"
            lines.append(_style_line(headline, selected=selected))
            lines.append(_style_line(detail, selected=selected, muted=not selected))

    lines.extend(["", "<열기> <돌아가기>", "명령: ↑↓ 이동 / Enter 열기 / Esc·Backspace 뒤로 / b"])
    return render_plain_box(lines)



def _json_block_lines(title: str, payload: Any) -> list[str]:
    lines = [title]
    rendered = json.dumps(payload if payload is not None else {}, ensure_ascii=False, indent=2)
    for line in rendered.splitlines():
        lines.append(f"  {line}")
    return lines



def _step_related_events(state: TaskBrowserState, step_run_id: str | None) -> list[dict[str, Any]]:
    if not step_run_id:
        return []
    return [event for event in state.detail_events if event.get("step_run_id") == step_run_id]



def render_tasks_browser_step_detail(state: TaskBrowserState) -> str:
    task = state.detail_task or {}
    step = _selected_step_item(state) or {}
    related_events = _step_related_events(state, step.get("step_run_id"))[-5:]

    lines = [
        f"Tasks > {_task_detail_title(task)} > {_truncate_text(step.get('title') or step.get('step_type') or '-', limit=36)}",
        f"상태: {step.get('status') or '-'}",
        f"설명: {_truncate_text(step.get('summary_message') or '요약 없음', limit=84)}",
        f"step_order: {step.get('step_order') or '-'}   type: {step.get('step_type') or '-'}",
        f"최근 갱신: {_format_time(step.get('updated_at') or step.get('created_at'))}",
        "",
    ]

    lines.extend(_json_block_lines("input_payload", step.get("input_payload") or {}))
    lines.append("")
    lines.extend(_json_block_lines("output_payload", step.get("output_payload") or {}))
    lines.append("")
    lines.extend(_json_block_lines("wait_payload", step.get("wait_payload") or {}))
    lines.append("")
    lines.extend(_json_block_lines("detail_json", step.get("detail_json") or {}))
    lines.append("")
    lines.append("최근 step event")
    if related_events:
        for event in related_events:
            lines.append(f"- {event.get('event_type') or '-'} | {event.get('summary_message') or event.get('status') or '-'}")
    else:
        lines.append("- 연결된 step event 없음")

    lines.extend(["", "<돌아가기>", "명령: Esc·Backspace 뒤로 / b"])
    return render_plain_box(lines)



def _clear_terminal() -> None:
    if sys.stdout.isatty():
        print("\033[2J\033[H", end="")
    else:
        print()



def _supports_windows_browser_keys() -> bool:
    return bool(os.name == "nt" and msvcrt is not None and sys.stdin.isatty() and sys.stdout.isatty())



def _read_browser_command(prompt_text: str, *, input_func: InputFunc = input) -> str:
    """tasks 브라우저 전용 입력을 읽는다.

    기본 input()만 쓰면 방향키가 일반 문자열 입력으로 흘러가 버린다.
    Windows 콘솔에서는 msvcrt 로 화살표/엔터/ESC/백스페이스를 직접 읽고,
    그 외 환경은 기존 문자열 입력으로 자연스럽게 fallback 한다.
    """

    if not _supports_windows_browser_keys() or input_func is not input:
        return input_func(prompt_text)

    print(prompt_text, end="", flush=True)
    buffer = ""
    while True:
        key = msvcrt.getwch()
        if key == "\x03":
            raise KeyboardInterrupt
        if key in {"\r", "\n"}:
            print()
            return buffer
        if key == "\x1b":
            print()
            return "__browser_back__"
        if key == "\b":
            if buffer:
                buffer = buffer[:-1]
                print("\b \b", end="", flush=True)
            else:
                print()
                return "__browser_back__"
            continue
        if key in {"\x00", "\xe0"}:
            code = msvcrt.getwch()
            print()
            if code == "H":
                return "__browser_up__"
            if code == "P":
                return "__browser_down__"
            if code == "K":
                return "__browser_prev__"
            if code == "M":
                return "__browser_next__"
            continue
        buffer += key
        print(key, end="", flush=True)



def _load_list(client, settings: Settings, state: TaskBrowserState) -> None:
    state.list_payload = fetch_tasks_page(client, settings, status_filter=state.status_filter, page=state.page, page_size=state.page_size)
    _clamp_selected_index(state)



def _load_detail(client, settings: Settings, state: TaskBrowserState, task_run_id: str) -> None:
    bundle = fetch_task_detail_bundle(client, settings, task_run_id)
    state.detail_task = bundle["task"]
    state.detail_steps = bundle["steps"]
    state.detail_events = bundle["events"]
    state.selected_task_id = task_run_id
    state.selected_step_index = 0
    state.depth = "task_detail"



def _update_filter(state: TaskBrowserState, next_filter: str) -> None:
    state.status_filter = next_filter
    state.page = 1
    state.selected_index = 0
    state.depth = "task_list"



def _normalize_command(raw_command: str) -> str:
    command = raw_command.lower()
    if command == "__browser_up__":
        return "up"
    if command == "__browser_down__":
        return "down"
    if command == "__browser_prev__":
        return "prev"
    if command == "__browser_next__":
        return "next"
    if command == "__browser_back__":
        return "back"
    return command



def _open_selected_task(client, settings: Settings, state: TaskBrowserState) -> None:
    selected_item = _selected_task_item(state)
    if selected_item is None:
        return
    _load_detail(client, settings, state, str(selected_item.get("task_run_id")))



def _open_selected_step(state: TaskBrowserState) -> None:
    if _selected_step_item(state) is None:
        return
    state.depth = "step_detail"



def _handle_task_list_command(client, settings: Settings, state: TaskBrowserState, *, raw_command: str, command: str, output_func: OutputFunc) -> None:
    if command in {"b", "back", "돌아가기", "q", "quit", "exit"}:
        raise TaskBrowserExit
    if command in {"j", "down", "up", "k"}:
        state.selected_index += 1 if command in {"j", "down"} else -1
        _clamp_selected_index(state)
        return
    if command in {"<", "p", "prev", "이전"}:
        if state.list_payload.get("has_previous"):
            state.page = max(1, state.page - 1)
            state.selected_index = 0
            _load_list(client, settings, state)
        return
    if command in {">", "n", "next", "다음"}:
        if state.list_payload.get("has_next"):
            state.page += 1
            state.selected_index = 0
            _load_list(client, settings, state)
        return
    if command in {alias.lower() for alias in FILTER_ALIASES}:
        normalized_filter = normalize_browser_filter(raw_command)
        if normalized_filter in TASK_BROWSER_FILTERS:
            _update_filter(state, normalized_filter)
            _load_list(client, settings, state)
        return
    if command in {"", "o", "open", "열기"}:
        _open_selected_task(client, settings, state)
        return
    if raw_command.isdigit():
        target_index = int(raw_command) - 1
        items = state.list_payload.get("items") or []
        if 0 <= target_index < len(items):
            state.selected_index = target_index
            _open_selected_task(client, settings, state)
        return
    if raw_command:
        output_func("알 수 없는 입력이야. 방향키, Enter, 숫자, 필터 키워드를 써줘.")



def _handle_task_detail_command(state: TaskBrowserState, *, command: str) -> None:
    if command in {"b", "back", "돌아가기", "q", "quit", "exit"}:
        state.depth = "task_list"
        return
    if command in {"j", "down", "up", "k"}:
        state.selected_step_index += 1 if command in {"j", "down"} else -1
        _clamp_selected_step_index(state)
        return
    if command in {"", "o", "open", "열기", "next"}:
        _open_selected_step(state)
        return



def _handle_step_detail_command(state: TaskBrowserState, *, command: str) -> None:
    if command in {"b", "back", "돌아가기", "q", "quit", "exit"}:
        state.depth = "task_detail"



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
        if state.depth == "task_list":
            output_func(render_tasks_browser_list(state))
        elif state.depth == "task_detail":
            output_func(_render_task_detail(state))
        else:
            output_func(render_tasks_browser_step_detail(state))

        try:
            raw_command = _read_browser_command("tasks> ", input_func=input_func).strip()
        except (EOFError, KeyboardInterrupt):
            output_func("작업 브라우저를 닫을게.")
            return

        command = _normalize_command(raw_command)
        try:
            if state.depth == "task_list":
                _handle_task_list_command(client, settings, state, raw_command=raw_command, command=command, output_func=output_func)
            elif state.depth == "task_detail":
                _handle_task_detail_command(state, command=command)
            else:
                _handle_step_detail_command(state, command=command)
        except TaskBrowserExit:
            output_func("작업 브라우저를 닫을게.")
            return
