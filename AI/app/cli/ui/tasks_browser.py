from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
import os
import shutil
import sys
from typing import Any, Callable
from urllib.parse import urlencode

try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None  # type: ignore[assignment]

try:
    from prompt_toolkit.application import Application
    from prompt_toolkit.formatted_text import ANSI
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout import Layout
    from prompt_toolkit.layout.containers import Window
    from prompt_toolkit.layout.controls import FormattedTextControl
except ImportError:  # pragma: no cover
    Application = None  # type: ignore[assignment]
    ANSI = None  # type: ignore[assignment]
    KeyBindings = None  # type: ignore[assignment]
    Layout = None  # type: ignore[assignment]
    Window = None  # type: ignore[assignment]
    FormattedTextControl = None  # type: ignore[assignment]

from app.cli.core.transport import request_path
from app.cli.ui.output import render_plain_box
from app.core.config import Settings

InputFunc = Callable[[str], str]
OutputFunc = Callable[[str], None]

TASK_BROWSER_FILTERS: list[tuple[str, str]] = [
    ("ALL", "전체"),
    ("RUNNING", "진행중"),
    ("WAITING", "대기"),
    ("COMPLETED", "완료"),
]
TASK_FILTER_CODES = {code for code, _ in TASK_BROWSER_FILTERS}

TASK_TITLE_FALLBACKS = {
    "agent.loop": "agent loop 실행",
}
STEP_TITLE_FALLBACKS = {
    "agent.loop.execute": "agent loop 실행 단계",
    "echo.execute": "입력 메시지 반영",
    "delegate.child": "Child Echo 위임",
    "approval.wait": "사용자 승인 대기",
}
SUMMARY_FALLBACKS = {
    "agent loop completed": "agent loop 완료",
    "echo executor completed": "입력 메시지 반영 완료",
    "child delegation completed": "Child 세션 위임 완료",
    "approval required": "사용자 승인이 필요함",
    "approval completed": "사용자 승인 완료",
}
_ACTIVE_STEP_STATUSES = {"PENDING", "RUNNING", "WAITING", "BLOCKED"}

_ANSI_RESET = "\033[0m"
# shell slash menu 에서 보이는 파란 계열과 최대한 맞춘다.
_ANSI_SELECTED = "\033[38;5;45m"
_ANSI_MUTED = "\033[90m"
_ANSI_ACCENT = "\033[38;5;45m"


@dataclass(slots=True)
class TaskBrowserState:
    # 본문 리스트에서 현재 커서 위치
    selected_index: int = 0
    # step 리스트에서 현재 커서 위치
    selected_step_index: int = 0
    # footer 액션 포커스 여부와 위치
    focus_area: str = "body"
    footer_index: int = 0

    status_filter: str = "ALL"
    page: int = 1
    page_size: int = 8
    depth: str = "task_list"
    list_payload: dict[str, Any] = field(default_factory=dict)
    detail_task: dict[str, Any] | None = None
    detail_steps: list[dict[str, Any]] = field(default_factory=list)
    detail_events: list[dict[str, Any]] = field(default_factory=list)
    selected_task_id: str | None = None


@dataclass(frozen=True, slots=True)
class BrowserAction:
    key: str
    label: str


TASK_LIST_ACTIONS = [
    BrowserAction("filter", "<필터>"),
    BrowserAction("prev", "<이전>"),
    BrowserAction("next", "<다음>"),
    BrowserAction("open", "<열기>"),
    BrowserAction("back", "<돌아가기>"),
]
TASK_DETAIL_ACTIONS = [
    BrowserAction("open", "<Step 열기>"),
    BrowserAction("back", "<돌아가기>"),
]
STEP_DETAIL_ACTIONS = [BrowserAction("back", "<돌아가기>")]


class TaskBrowserRequestError(RuntimeError):
    pass


class TaskBrowserExit(Exception):
    pass


class TaskBrowserInputEnded(Exception):
    pass



def normalize_browser_filter(raw_value: str | None) -> str:
    if raw_value is None:
        return "ALL"
    normalized = str(raw_value).strip().upper()
    return normalized if normalized in TASK_FILTER_CODES else "ALL"



def build_tasks_list_path(settings: Settings, *, status_filter: str, page: int, page_size: int) -> str:
    query = urlencode({"status": status_filter, "page": page, "page_size": page_size})
    return request_path(settings, f"/taskRuns?{query}")



def _raise_request_error(response, payload: Any, *, action: str) -> None:
    status_code = getattr(response, "status_code", None)
    detail = payload.get("detail") if isinstance(payload, dict) else None

    if action == "list" and status_code == 405:
        raise TaskBrowserRequestError("현재 실행 중인 서버가 아직 GET /taskRuns 를 지원하지 않아. 최신 코드 반영 후 서버를 재시작해 줘.")
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
    task_response = client.request("GET", request_path(settings, f"/taskRuns/{task_run_id}"))
    steps_response = client.request("GET", request_path(settings, f"/taskRuns/{task_run_id}/steps"))
    events_response = client.request("GET", request_path(settings, f"/taskRuns/{task_run_id}/events"))

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



def _truncate_text(value: str | None, *, limit: int = 64) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text or "-"
    return text[: limit - 1].rstrip() + "…"



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



def _friendly_task_title(payload: dict[str, Any]) -> str:
    title = str(payload.get("title") or "").strip()
    task_type = str(payload.get("task_type") or "").strip()
    intent_type = str(payload.get("intent_type") or "").strip()
    if title and title not in {task_type, intent_type}:
        return _truncate_text(title, limit=42)
    return _truncate_text(TASK_TITLE_FALLBACKS.get(task_type) or TASK_TITLE_FALLBACKS.get(intent_type) or intent_type or task_type or "Task", limit=42)



def _friendly_step_title(payload: dict[str, Any]) -> str:
    title = str(payload.get("title") or "").strip()
    step_type = str(payload.get("step_type") or "").strip()
    if title and title != step_type:
        return _truncate_text(title, limit=42)
    return _truncate_text(STEP_TITLE_FALLBACKS.get(step_type) or step_type or "Step", limit=42)



def _friendly_summary(raw_value: str | None, *, fallback_title: str) -> str:
    summary = str(raw_value or "").strip()
    if not summary:
        return fallback_title
    return _truncate_text(SUMMARY_FALLBACKS.get(summary.lower()) or summary, limit=64)



def _task_input_summary(payload: dict[str, Any]) -> str:
    summary = payload.get("input_summary")
    if summary:
        return _truncate_text(summary, limit=64)
    progress = payload.get("progress_summary")
    if progress:
        return _truncate_text(progress, limit=64)
    return "입력 요약 없음"



def _task_detail_input_summary(task: dict[str, Any]) -> str:
    input_payload = task.get("input_payload") or {}
    preferred = [
        input_payload.get("prompt"),
        input_payload.get("message"),
        input_payload.get("subject"),
        input_payload.get("title"),
        input_payload.get("content"),
        input_payload.get("text"),
    ]
    for value in preferred:
        if isinstance(value, str) and value.strip():
            return _truncate_text(value, limit=80)
    return _truncate_text(str(input_payload), limit=80) if input_payload else "입력 요약 없음"



def _current_step_summary(payload: dict[str, Any]) -> str:
    current_step = payload.get("current_step") or {}
    fallback_title = _friendly_step_title(current_step) if current_step else "현재 단계 없음"
    return _friendly_summary(current_step.get("summary_message") or payload.get("progress_summary"), fallback_title=fallback_title)



def _select_current_step(steps: list[dict[str, Any]]) -> dict[str, Any] | None:
    for step in steps:
        if step.get("status") in _ACTIVE_STEP_STATUSES:
            return step
    return steps[-1] if steps else None



def _format_time(raw_value: str | None) -> str:
    if not raw_value:
        return "-"
    return raw_value.replace("T", " ").replace("Z", "").split("+")[0]



def _footer_actions_for_depth(depth: str) -> list[BrowserAction]:
    if depth == "task_list":
        return TASK_LIST_ACTIONS
    if depth == "task_detail":
        return TASK_DETAIL_ACTIONS
    return STEP_DETAIL_ACTIONS



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



def _clamp_footer_index(state: TaskBrowserState) -> None:
    actions = _footer_actions_for_depth(state.depth)
    if not actions:
        state.footer_index = 0
        return
    state.footer_index = max(0, min(state.footer_index, len(actions) - 1))



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



def _render_filter_tabs(selected_filter: str) -> str:
    segments: list[str] = []
    for code, label in TASK_BROWSER_FILTERS:
        token = f"[{label}]" if code == selected_filter else label
        segments.append(_style_line(token, accent=(code == selected_filter)))
    return " / ".join(segments)



def _render_footer_actions(state: TaskBrowserState) -> str:
    segments: list[str] = []
    footer_focused = state.focus_area == "footer"
    for index, action in enumerate(_footer_actions_for_depth(state.depth)):
        selected = footer_focused and index == state.footer_index
        token = f"[{action.label}]" if selected else action.label
        segments.append(_style_line(token, selected=selected, muted=footer_focused and not selected))
    return " ".join(segments)



def _render_task_preview_lines(state: TaskBrowserState) -> list[str]:
    selected = _selected_task_item(state)
    if selected is None:
        return ["선택 미리보기", "- 항목 없음"]
    return [
        "선택 미리보기",
        f"- 제목: {_friendly_task_title(selected)}",
        f"- 입력: {_task_input_summary(selected)}",
        f"- 현재: {_current_step_summary(selected)}",
        f"- step: {selected.get('step_count') or 0}개",
    ]



def _render_step_preview_lines(state: TaskBrowserState) -> list[str]:
    selected = _selected_step_item(state)
    current_step = _select_current_step(state.detail_steps)
    if selected is None:
        return ["선택 step 미리보기", "- step 없음"]
    selected_id = selected.get("step_run_id")
    current_id = current_step.get("step_run_id") if current_step else None
    relation = "현재 실행 단계" if selected_id == current_id else "선택된 단계"
    return [
        "선택 step 미리보기",
        f"- 단계: {_friendly_step_title(selected)}",
        f"- 설명: {_friendly_summary(selected.get('summary_message'), fallback_title=_friendly_step_title(selected))}",
        f"- 상태: {selected.get('status') or '-'} ({relation})",
    ]



def _terminal_height() -> int:
    return max(16, shutil.get_terminal_size((120, 30)).lines)



def _viewport_bounds(*, selected_index: int, total_items: int, item_height: int, reserved_lines: int) -> tuple[int, int]:
    if total_items <= 0:
        return (0, 0)

    available_lines = max(1, _terminal_height() - reserved_lines)
    visible_items = max(1, available_lines // item_height)
    start = max(0, min(selected_index - (visible_items // 2), total_items - visible_items))
    end = min(total_items, start + visible_items)
    return (start, end)



def render_tasks_browser_list(state: TaskBrowserState) -> str:
    payload = state.list_payload or {}
    items = payload.get("items") or []
    total_count = int(payload.get("total_count") or 0)
    page = int(payload.get("page") or 1)
    page_size = int(payload.get("page_size") or max(1, state.page_size))
    total_pages = max(1, math.ceil(total_count / page_size)) if total_count else 1

    footer_lines = [
        "",
        _render_footer_actions(state),
        "조작: ↑↓ 목록 이동 / ←→ 페이지 이동 / Tab 액션 이동 / Enter 실행 / Esc 뒤로",
    ]
    header_lines = [
        "Tasks",
        f"필터: {_render_filter_tabs(state.status_filter)}",
        f"페이지: {page}/{total_pages}   총 {total_count}개",
        "",
        *_render_task_preview_lines(state),
        "",
    ]

    lines = list(header_lines)

    if not items:
        lines.extend(["Task 목록", "표시할 작업이 없습니다."])
    else:
        start, end = _viewport_bounds(
            selected_index=state.selected_index,
            total_items=len(items),
            item_height=4,
            reserved_lines=len(header_lines) + len(footer_lines) + 3,
        )
        lines.append(f"Task 목록 ({start + 1}-{end} / {len(items)})")
        if start > 0:
            lines.append(_style_line(f"… 위에 {start}개 더 있음", muted=True))
        for index in range(start, end):
            item = items[index]
            cursor_selected = index == state.selected_index
            selected = cursor_selected and state.focus_area == "body"
            marker = "›" if cursor_selected else " "
            title = _friendly_task_title(item)
            status = str(item.get("status") or "-")
            step_count = int(item.get("step_count") or 0)
            headline = f"{marker} [{index + 1}] {title} | {status} | step {step_count}개"
            detail = f"    입력: {_task_input_summary(item)}"
            progress = f"    현재: {_current_step_summary(item)}"
            meta = f"    id: {item.get('task_run_id') or '-'} • updated: {_format_time(item.get('updated_at') or item.get('created_at'))}"
            lines.append(_style_line(headline, selected=selected))
            lines.append(_style_line(detail, selected=selected, muted=not selected))
            lines.append(_style_line(progress, selected=selected, muted=not selected))
            lines.append(_style_line(meta, selected=selected, muted=not selected))
        if end < len(items):
            lines.append(_style_line(f"… 아래에 {len(items) - end}개 더 있음", muted=True))

    lines.extend(footer_lines)
    return render_plain_box(lines)



def render_task_detail(state: TaskBrowserState) -> str:
    task = state.detail_task or {}
    steps = state.detail_steps or []
    current_step = _select_current_step(steps)
    current_step_id = current_step.get("step_run_id") if current_step else None

    footer_lines = [
        "",
        _render_footer_actions(state),
        "조작: ↑↓ step 이동 / ←→ 액션 이동 / Tab 액션 이동 / Enter 실행 / Esc 뒤로",
    ]
    header_lines = [
        f"Tasks > {_friendly_task_title(task)}",
        f"상태: {task.get('status') or '-'}",
        f"입력: {_task_detail_input_summary(task)}",
        "TaskRun = 전체 작업 / StepRun = 한 단계 / detail_json = step 저장 실행 정보",
        f"step: {len(steps)}개   executor: {task.get('entry_executor_key') or '-'}",
        f"최근 갱신: {_format_time(task.get('updated_at') or task.get('created_at'))}",
        "",
        *_render_step_preview_lines(state),
        "",
    ]

    lines = list(header_lines)

    if not steps:
        lines.extend(["Step 목록", "step 이 없습니다."])
    else:
        start, end = _viewport_bounds(
            selected_index=state.selected_step_index,
            total_items=len(steps),
            item_height=2,
            reserved_lines=len(header_lines) + len(footer_lines) + 3,
        )
        lines.append(f"Step 목록 ({start + 1}-{end} / {len(steps)})")
        if start > 0:
            lines.append(_style_line(f"… 위에 {start}개 더 있음", muted=True))
        for index in range(start, end):
            step = steps[index]
            cursor_selected = index == state.selected_step_index
            selected = cursor_selected and state.focus_area == "body"
            active = step.get("step_run_id") == current_step_id
            marker = "›" if cursor_selected else " "
            badge = "현재" if active else f"#{index + 1}"
            title = _friendly_step_title(step)
            summary = _friendly_summary(step.get("summary_message"), fallback_title=title)
            headline = f"{marker} [{badge}] {title} | {step.get('status') or '-'}"
            detail = f"    설명: {summary}"
            if active and cursor_selected:
                detail += " (선택됨, 현재 실행 단계)"
            elif active:
                detail += " (현재 실행 단계)"
            elif cursor_selected:
                detail += " (선택됨)"
            lines.append(_style_line(headline, selected=selected, accent=active and not selected))
            lines.append(_style_line(detail, selected=selected, muted=not selected and not active))
        if end < len(steps):
            lines.append(_style_line(f"… 아래에 {len(steps) - end}개 더 있음", muted=True))

    lines.extend(footer_lines)
    return render_plain_box(lines)



def _json_block_lines(title: str, payload: Any) -> list[str]:
    lines = [title]
    rendered = json.dumps(payload if payload is not None else {}, ensure_ascii=False, indent=2)
    for line in rendered.splitlines():
        lines.append(f"  {line}")
    return lines



def _step_detail_summary_lines(step: dict[str, Any]) -> list[str]:
    detail = step.get("detail_json") or {}
    agent_detail = detail.get("agentDetail") or {}
    tool_detail = detail.get("toolDetail") or {}
    llm_detail = detail.get("llmDetail") or {}
    operation_detail = detail.get("operationDetail") or {}
    planning_detail = detail.get("planningDetail") or {}
    tool_names = ", ".join(tool_detail.get("toolNames") or []) or "없음"
    return [
        f"- Agent 호출: {'yes' if agent_detail.get('called') else 'no'}",
        f"- Agent 상태: {agent_detail.get('status') or '-'}",
        f"- Tool 사용: {tool_names}",
        f"- LLM 호출: {llm_detail.get('callCount') or 0}회 ({llm_detail.get('model') or '-'})",
        f"- Operation: {operation_detail.get('completedCount') or 0}/{operation_detail.get('totalCount') or 0}",
        f"- 남은 todo: {planning_detail.get('currentKey') or '없음'}",
        f"- Child task: {agent_detail.get('childTaskRunId') or '없음'}",
        f"- Child 요약: {agent_detail.get('summary') or '없음'}",
    ]



def render_tasks_browser_step_detail(state: TaskBrowserState) -> str:
    task = state.detail_task or {}
    step = _selected_step_item(state) or {}
    related_events = [event for event in state.detail_events if event.get("step_run_id") == step.get("step_run_id")][-5:]

    lines = [
        f"Tasks > {_friendly_task_title(task)} > {_friendly_step_title(step)}",
        f"상태: {step.get('status') or '-'}",
        f"설명: {_friendly_summary(step.get('summary_message'), fallback_title=_friendly_step_title(step))}",
        f"step_order: {step.get('step_order') or '-'}   type: {step.get('step_type') or '-'}",
        f"최근 갱신: {_format_time(step.get('updated_at') or step.get('created_at'))}",
        "",
        "detail 해석",
        *_step_detail_summary_lines(step),
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

    lines.extend(
        [
            "",
            _render_footer_actions(state),
            "조작: ←→ 액션 이동 / Enter 실행 / Esc 뒤로",
        ]
    )
    return render_plain_box(lines)



def _render_current_view(state: TaskBrowserState) -> str:
    if state.depth == "task_list":
        return render_tasks_browser_list(state)
    if state.depth == "task_detail":
        return render_task_detail(state)
    return render_tasks_browser_step_detail(state)



def _clear_terminal() -> None:
    if sys.stdout.isatty():
        print("\033[2J\033[H", end="")
    else:
        print()



def _supports_windows_browser_keys() -> bool:
    return bool(os.name == "nt" and msvcrt is not None and sys.stdin.isatty() and sys.stdout.isatty())



def _supports_fullscreen_browser() -> bool:
    return bool(
        Application
        and ANSI
        and KeyBindings
        and Layout
        and Window
        and FormattedTextControl
        and sys.stdin.isatty()
        and sys.stdout.isatty()
    )



def _read_browser_command(*, input_func: InputFunc = input) -> str:
    if input_func is not input:
        raw = str(input_func(""))
        if not raw:
            raise TaskBrowserInputEnded
        return raw.strip().lower()

    if not _supports_windows_browser_keys():
        raise TaskBrowserInputEnded

    while True:
        key = msvcrt.getwch()
        if key == "\x03":
            raise KeyboardInterrupt
        if key in {"\r", "\n"}:
            return "enter"
        if key == "\x1b":
            return "back"
        if key == "\b":
            return "back"
        if key == "\t":
            return "tab"
        if key in {"\x00", "\xe0"}:
            code = msvcrt.getwch()
            if code == "H":
                return "up"
            if code == "P":
                return "down"
            if code == "K":
                return "left"
            if code == "M":
                return "right"



def _load_list(client, settings: Settings, state: TaskBrowserState) -> None:
    state.list_payload = fetch_tasks_page(client, settings, status_filter=state.status_filter, page=state.page, page_size=state.page_size)
    _clamp_selected_index(state)
    state.depth = "task_list"
    state.focus_area = "body"
    state.footer_index = 0



def _load_detail(client, settings: Settings, state: TaskBrowserState, task_run_id: str) -> None:
    bundle = fetch_task_detail_bundle(client, settings, task_run_id)
    state.detail_task = bundle["task"]
    state.detail_steps = bundle["steps"]
    state.detail_events = bundle["events"]
    state.selected_task_id = task_run_id
    state.selected_step_index = 0
    state.depth = "task_detail"
    state.focus_area = "body"
    state.footer_index = 0
    _clamp_selected_step_index(state)



def _cycle_filter(state: TaskBrowserState) -> None:
    codes = [code for code, _ in TASK_BROWSER_FILTERS]
    current_index = codes.index(state.status_filter) if state.status_filter in codes else 0
    state.status_filter = codes[(current_index + 1) % len(codes)]
    state.page = 1
    state.selected_index = 0



def _execute_footer_action(client, settings: Settings, state: TaskBrowserState) -> None:
    action = _footer_actions_for_depth(state.depth)[state.footer_index]

    if state.depth == "task_list":
        if action.key == "filter":
            _cycle_filter(state)
            _load_list(client, settings, state)
            state.focus_area = "footer"
            state.footer_index = 0
            return
        if action.key == "prev":
            if state.list_payload.get("has_previous"):
                state.page = max(1, state.page - 1)
                _load_list(client, settings, state)
                state.focus_area = "footer"
                state.footer_index = 1
            return
        if action.key == "next":
            if state.list_payload.get("has_next"):
                state.page += 1
                _load_list(client, settings, state)
                state.focus_area = "footer"
                state.footer_index = 2
            return
        if action.key == "open":
            selected = _selected_task_item(state)
            if selected is not None:
                _load_detail(client, settings, state, str(selected.get("task_run_id")))
            return
        if action.key == "back":
            raise TaskBrowserExit
        return

    if state.depth == "task_detail":
        if action.key == "open":
            if _selected_step_item(state) is not None:
                state.depth = "step_detail"
                state.focus_area = "footer"
                state.footer_index = 0
            return
        if action.key == "back":
            state.depth = "task_list"
            state.focus_area = "body"
            state.footer_index = 0
            return
        return

    if action.key == "back":
        state.depth = "task_detail"
        state.focus_area = "body"
        state.footer_index = 0



def _handle_task_list_command(client, settings: Settings, state: TaskBrowserState, command: str) -> None:
    if command == "back":
        raise TaskBrowserExit

    if command == "tab":
        state.focus_area = "footer" if state.focus_area == "body" else "body"
        return

    if state.focus_area == "footer":
        if command == "left":
            state.footer_index -= 1
            _clamp_footer_index(state)
            return
        if command == "right":
            state.footer_index += 1
            _clamp_footer_index(state)
            return
        if command == "up":
            state.focus_area = "body"
            return
        if command == "enter":
            _execute_footer_action(client, settings, state)
            return
        return

    # 본문에서는 위아래만 항목 이동, 마지막 항목 아래에서는 footer 로 내려간다.
    if command == "up":
        state.selected_index -= 1
        _clamp_selected_index(state)
        return
    if command == "down":
        items = state.list_payload.get("items") or []
        if not items:
            state.focus_area = "footer"
            state.footer_index = 0
            _clamp_footer_index(state)
            return
        if state.selected_index >= len(items) - 1:
            state.focus_area = "footer"
            state.footer_index = 0
            _clamp_footer_index(state)
            return
        state.selected_index += 1
        _clamp_selected_index(state)
        return
    if command == "left":
        if state.list_payload.get("has_previous"):
            state.page = max(1, state.page - 1)
            _load_list(client, settings, state)
        return
    if command == "right":
        if state.list_payload.get("has_next"):
            state.page += 1
            _load_list(client, settings, state)
        return
    if command == "enter":
        selected = _selected_task_item(state)
        if selected is not None:
            _load_detail(client, settings, state, str(selected.get("task_run_id")))



def _handle_task_detail_command(client, settings: Settings, state: TaskBrowserState, command: str) -> None:
    del client, settings

    if command == "back":
        state.depth = "task_list"
        state.focus_area = "body"
        state.footer_index = 0
        return

    if command == "tab":
        state.focus_area = "footer" if state.focus_area == "body" else "body"
        return

    if state.focus_area == "footer":
        if command == "left":
            state.footer_index -= 1
            _clamp_footer_index(state)
            return
        if command == "right":
            state.footer_index += 1
            _clamp_footer_index(state)
            return
        if command == "up":
            state.focus_area = "body"
            return
        if command == "enter":
            if TASK_DETAIL_ACTIONS[state.footer_index].key == "open":
                if _selected_step_item(state) is not None:
                    state.depth = "step_detail"
                    state.focus_area = "footer"
                    state.footer_index = 0
            else:
                state.depth = "task_list"
                state.focus_area = "body"
                state.footer_index = 0
            return
        return

    # detail body 는 수직 리스트다. 마지막 step 아래에서는 footer 로 내려간다.
    if command == "up":
        state.selected_step_index -= 1
        _clamp_selected_step_index(state)
        return
    if command == "down":
        if state.detail_steps and state.selected_step_index >= len(state.detail_steps) - 1:
            state.focus_area = "footer"
            state.footer_index = 0
            _clamp_footer_index(state)
            return
        state.selected_step_index += 1
        _clamp_selected_step_index(state)
        return
    if command == "enter":
        if _selected_step_item(state) is not None:
            state.depth = "step_detail"
            state.focus_area = "footer"
            state.footer_index = 0



def _handle_step_detail_command(state: TaskBrowserState, command: str) -> None:
    if command in {"back", "enter"}:
        state.depth = "task_detail"
        state.focus_area = "body"
        state.footer_index = 0
        return

    if command == "tab":
        state.focus_area = "footer"
        state.footer_index = 0
        return

    if command in {"left", "right", "up", "down"}:
        state.footer_index = 0



def _dispatch_command(client, settings: Settings, state: TaskBrowserState, command: str) -> None:
    if state.depth == "task_list":
        _handle_task_list_command(client, settings, state, command)
        return
    if state.depth == "task_detail":
        _handle_task_detail_command(client, settings, state, command)
        return
    _handle_step_detail_command(state, command)



def _run_tasks_browser_fallback(client, settings: Settings, state: TaskBrowserState, *, input_func: InputFunc, output_func: OutputFunc) -> None:
    while True:
        _clear_terminal()
        output_func(_render_current_view(state))

        try:
            command = _read_browser_command(input_func=input_func)
        except (EOFError, KeyboardInterrupt, TaskBrowserInputEnded):
            output_func("작업 브라우저를 닫을게.")
            return

        try:
            _dispatch_command(client, settings, state, command)
        except TaskBrowserExit:
            output_func("작업 브라우저를 닫을게.")
            return



def _run_tasks_browser_fullscreen(client, settings: Settings, state: TaskBrowserState) -> None:
    control = FormattedTextControl(lambda: ANSI(_render_current_view(state)))
    window = Window(content=control, always_hide_cursor=True, wrap_lines=False)
    bindings = KeyBindings()
    app: Application | None = None

    def _apply(command: str, event) -> None:  # pragma: no cover - interactive only
        try:
            _dispatch_command(client, settings, state, command)
        except TaskBrowserExit:
            event.app.exit(result="closed")
            return
        event.app.invalidate()

    @bindings.add("up")
    def _(event) -> None:  # pragma: no cover - interactive only
        _apply("up", event)

    @bindings.add("down")
    def _(event) -> None:  # pragma: no cover - interactive only
        _apply("down", event)

    @bindings.add("left")
    def _(event) -> None:  # pragma: no cover - interactive only
        _apply("left", event)

    @bindings.add("right")
    def _(event) -> None:  # pragma: no cover - interactive only
        _apply("right", event)

    @bindings.add("tab")
    def _(event) -> None:  # pragma: no cover - interactive only
        _apply("tab", event)

    @bindings.add("enter")
    def _(event) -> None:  # pragma: no cover - interactive only
        _apply("enter", event)

    @bindings.add("escape")
    @bindings.add("backspace")
    def _(event) -> None:  # pragma: no cover - interactive only
        _apply("back", event)

    @bindings.add("c-c")
    def _(event) -> None:  # pragma: no cover - interactive only
        event.app.exit(result="closed")

    app = Application(layout=Layout(window), key_bindings=bindings, full_screen=True, mouse_support=False)
    app.run()
    del app



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

    if input_func is input and _supports_fullscreen_browser():
        _run_tasks_browser_fullscreen(client, settings, state)
        return

    _run_tasks_browser_fallback(client, settings, state, input_func=input_func, output_func=output_func)
