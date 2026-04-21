import base64
import importlib
import json
import os
import time
from collections import deque

import pytest
from prompt_toolkit.document import Document

from app.cli import RemoteCLIClient, _SlashCommandCompleter, _should_open_slash_menu, build_parser, main
import app.cli.ui.prompt as PROMPT_UI
import app.cli.ui.tasks_browser as TASK_BROWSER_UI
from app.core.config import get_settings
from app.cli.ui.output import _display_width, render_box, render_plain_box

CLI_MAIN_MODULE = importlib.import_module("app.cli.main")


class FakeResponse:
    def __init__(self, payload, *, success: bool = True):
        self._payload = payload
        self.is_success = success

    def json(self):
        return self._payload


class FakeRemoteClient:
    def __init__(self, responses):
        self.responses = deque(responses)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def request(self, method, path, *, json_body=None):
        if not self.responses:
            raise AssertionError(f"unexpected request: {method} {path}")
        return self.responses.popleft()


def _make_test_access_token() -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none"}).encode()).decode().rstrip("=")
    payload = base64.urlsafe_b64encode(
        json.dumps({"exp": 4102444800, "scp": ["model.generate"], "https://api.openai.com/auth": {"chatgpt_account_id": "acct_test"}}).encode()
    ).decode().rstrip("=")
    return f"{header}.{payload}.sig"


def test_remote_client_does_not_duplicate_api_prefix():
    client = RemoteCLIClient(base_url="http://127.0.0.1:8000/api/v1", timeout_seconds=10)

    assert client._normalize_request_path("/api/v1/providers/openai_oauth/auth") == "/providers/openai_oauth/auth"
    assert client._normalize_request_path("/api/v1/ready") == "/ready"


def test_slash_command_completer_matches_prefix():
    completer = _SlashCommandCompleter()
    completions = list(completer.get_completions(Document(text="/st", cursor_position=3), None))

    assert any(item.text == "/status" for item in completions)


def test_slash_command_completer_shows_menu_for_single_slash():
    completer = _SlashCommandCompleter()
    completions = list(completer.get_completions(Document(text="/", cursor_position=1), None))

    texts = {item.text for item in completions}
    assert "/help" in texts
    assert "/status" in texts
    assert "/tasks" in texts
    assert "/auth" in texts


def test_slash_command_completer_uses_codex_like_display_columns():
    completer = _SlashCommandCompleter()
    completion = next(iter(completer.get_completions(Document(text="/st", cursor_position=3), None)))

    display = list(completion.display)
    assert display[0] == ("class:completion-command", "/status")
    assert display[1][1].isspace()
    assert display[2] == ("class:completion-description", "show current provider and connection state")


def test_should_open_slash_menu_only_for_first_character():
    assert _should_open_slash_menu("", 0) is True
    assert _should_open_slash_menu("abc", 3) is False
    assert _should_open_slash_menu("/", 1) is False


def test_render_box_keeps_terminal_width_aligned():
    box = render_box(
        "HeyGent AI Shell",
        [
            ("model", "gpt-5.4"),
            ("directory", r"C:\Users\Jun\Desktop\saffy\Openclaw\S14P31E105\ai"),
            ("base-url", "http://127.0.0.1:8000/api/v1"),
        ],
        inner_padding=2,
        vertical_padding=1,
    )

    widths = {_display_width(line) for line in box.splitlines()}
    assert len(widths) == 1


def test_render_plain_box_keeps_terminal_width_aligned():
    box = render_plain_box(
        [
            "› HeyGent AI (v0.1.0)",
            "",
            "model:     gpt-5.4  /model to change",
            r"directory: ~\Desktop\saffy\Openclaw\S14P31E105\AI",
            "auth:      not connected  /auth to sign in",
        ]
    )

    widths = {_display_width(line) for line in box.splitlines()}
    assert len(widths) == 1


def test_render_plain_box_ignores_ansi_width_for_alignment():
    box = render_plain_box([
        "\033[97mselected line\033[0m",
        "plain line",
    ])

    widths = {_display_width(line) for line in box.splitlines()}
    assert len(widths) == 1


def test_tasks_browser_renders_task_step_and_step_detail_views(monkeypatch):
    monkeypatch.setattr(TASK_BROWSER_UI.sys.stdout, "isatty", lambda: False)
    state = TASK_BROWSER_UI.TaskBrowserState(
        status_filter="WAITING",
        list_payload={
            "items": [
                {
                    "task_run_id": "task_wait",
                    "task_type": "approval.wait",
                    "status": "WAITING",
                    "title": "승인 대기 태스크",
                    "input_summary": "배포 전 승인해줘",
                    "step_count": 2,
                    "updated_at": "2026-04-22T00:14:00",
                    "current_step": {"title": "사용자 승인 대기", "summary_message": "승인 응답을 기다리는 중"},
                }
            ],
            "page": 1,
            "page_size": 8,
            "total_count": 1,
        },
        detail_task={
            "task_run_id": "task_wait",
            "task_type": "approval.wait",
            "flow_name": "approval_wait_flow",
            "status": "WAITING",
            "title": "승인 대기 태스크",
            "input_payload": {"subject": "배포 전 승인해줘"},
            "updated_at": "2026-04-22T00:14:00",
        },
        detail_steps=[
            {
                "step_run_id": "step_plan",
                "step_order": 1,
                "step_type": "approval.plan",
                "status": "COMPLETED",
                "title": "승인 조건 정리",
                "summary_message": "어떤 승인이 필요한지 정리함",
                "input_payload": {"subject": "배포 전 승인해줘"},
                "output_payload": {"approvalReason": "배포 승인 필요"},
                "wait_payload": {},
                "detail_json": {"agentDetail": {"called": False}, "toolDetail": {"toolNames": []}, "llmDetail": {"model": None, "callCount": 0}},
            },
            {
                "step_run_id": "step_wait",
                "step_order": 2,
                "step_type": "approval.wait",
                "status": "WAITING",
                "title": "사용자 승인 대기",
                "summary_message": "승인 응답을 기다리는 중",
                "input_payload": {"subject": "배포 전 승인해줘"},
                "output_payload": {},
                "wait_payload": {"reason": "approval_required"},
                "detail_json": {
                    "agentDetail": {"called": False},
                    "toolDetail": {"toolNames": ["approval.request"]},
                    "llmDetail": {"model": "gpt-5.4", "callCount": 1},
                },
                "updated_at": "2026-04-22T00:14:00",
            },
        ],
        detail_events=[
            {"event_type": "approval.requested", "step_run_id": "step_wait", "summary_message": "승인이 필요합니다."},
        ],
        depth="step_detail",
        selected_step_index=1,
    )

    list_rendered = TASK_BROWSER_UI.render_tasks_browser_list(state)
    state.depth = "task_detail"
    task_detail_rendered = TASK_BROWSER_UI.render_task_detail(state)
    state.depth = "step_detail"
    step_detail_rendered = TASK_BROWSER_UI.render_tasks_browser_step_detail(state)

    assert "필터: 전체 / 진행중 / [대기] / 완료" in list_rendered
    assert "[<필터>]" not in list_rendered
    assert "Task 목록 (1-1 / 1)" in list_rendered
    assert "› [1] 승인 대기 태스크 | WAITING | step 2개" in list_rendered
    assert "입력: 배포 전 승인해줘" in list_rendered
    assert "현재: 승인 응답을 기다리는 중" in list_rendered
    assert "Tasks > 승인 대기 태스크" in task_detail_rendered
    assert "TaskRun = 전체 작업 / StepRun = 한 단계 / detail_json = step 저장 실행 정보" in task_detail_rendered
    assert "Step 목록 (1-2 / 2)" in task_detail_rendered
    assert "[현재] 사용자 승인 대기 | WAITING" in task_detail_rendered
    assert "Tasks > 승인 대기 태스크 > 사용자 승인 대기" in step_detail_rendered
    assert "detail 해석" in step_detail_rendered
    assert "- Tool 사용: approval.request" in step_detail_rendered
    assert '"reason": "approval_required"' in step_detail_rendered
    assert "- approval.requested | 승인이 필요합니다." in step_detail_rendered


def test_tasks_browser_explains_old_server_405():
    class FailingResponse:
        is_success = False
        status_code = 405

        def json(self):
            return {"detail": "Method Not Allowed"}

    class FailingClient:
        def request(self, method, path):
            return FailingResponse()

    with pytest.raises(TASK_BROWSER_UI.TaskBrowserRequestError) as error:
        TASK_BROWSER_UI.fetch_tasks_page(FailingClient(), get_settings(), status_filter="ALL", page=1, page_size=8)

    assert "GET /tasks" in str(error.value)
    assert "재시작" in str(error.value)


def test_tasks_browser_reads_windows_arrow_keys(monkeypatch):
    class FakeMsvcrt:
        def __init__(self, keys):
            self.keys = iter(keys)

        def getwch(self):
            return next(self.keys)

    monkeypatch.setattr(TASK_BROWSER_UI, "_supports_windows_browser_keys", lambda: True)
    monkeypatch.setattr(TASK_BROWSER_UI, "msvcrt", FakeMsvcrt(["\xe0", "H"]))

    assert TASK_BROWSER_UI._read_browser_command() == "up"


def test_tasks_browser_reads_windows_enter_and_tab(monkeypatch):
    class FakeMsvcrt:
        def __init__(self, keys):
            self.keys = iter(keys)

        def getwch(self):
            return next(self.keys)

    monkeypatch.setattr(TASK_BROWSER_UI, "_supports_windows_browser_keys", lambda: True)
    monkeypatch.setattr(TASK_BROWSER_UI, "msvcrt", FakeMsvcrt(["\t"]))
    assert TASK_BROWSER_UI._read_browser_command() == "tab"

    monkeypatch.setattr(TASK_BROWSER_UI, "msvcrt", FakeMsvcrt(["\r"]))
    assert TASK_BROWSER_UI._read_browser_command() == "enter"


def test_tasks_browser_run_flow_navigates_without_prompt(monkeypatch):
    settings = get_settings()
    outputs: list[str] = []
    commands = iter(["enter", "enter", "back", "back", "tab", "right", "right", "right", "right", "enter"])

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload
            self.is_success = True
            self.status_code = 200

        def json(self):
            return self._payload

    class FakeClient:
        def request(self, method, path):
            if "?" in path:
                return FakeResponse(
                    {
                        "items": [
                            {
                                "task_run_id": "task_1",
                                "task_type": "model.generate",
                                "flow_name": "model_generate_flow",
                                "status": "COMPLETED",
                                "title": "모델 생성 요청",
                                "input_summary": "헤르메스 알아?",
                                "step_count": 1,
                                "updated_at": "2026-04-22T00:00:00",
                                "current_step": {"step_run_id": "step_1", "step_type": "model.generate.execute", "status": "COMPLETED", "title": "모델 응답 생성", "summary_message": "모델 응답 생성 완료"},
                            }
                        ],
                        "page": 1,
                        "page_size": 8,
                        "total_count": 1,
                        "has_previous": False,
                        "has_next": False,
                        "status_filter": "ALL",
                    }
                )
            if path.endswith("/steps"):
                return FakeResponse(
                    [
                        {
                            "step_run_id": "step_1",
                            "task_run_id": "task_1",
                            "step_order": 1,
                            "step_type": "model.generate.execute",
                            "status": "COMPLETED",
                            "title": "모델 응답 생성",
                            "input_payload": {"prompt": "헤르메스 알아?"},
                            "output_payload": {"text": "응, 알아."},
                            "wait_payload": {},
                            "detail_json": {"agentDetail": {"called": False}, "toolDetail": {"toolNames": []}, "llmDetail": {"model": "gpt-5.4", "callCount": 1}},
                            "summary_message": "모델 응답 생성 완료",
                            "updated_at": "2026-04-22T00:00:00",
                        }
                    ]
                )
            if path.endswith("/events"):
                return FakeResponse([
                    {"event_type": "task.completed", "step_run_id": "step_1", "summary_message": "완료됨"}
                ])
            return FakeResponse(
                {
                    "task_run_id": "task_1",
                    "task_type": "model.generate",
                    "flow_name": "model_generate_flow",
                    "status": "COMPLETED",
                    "title": "모델 생성 요청",
                    "input_payload": {"prompt": "헤르메스 알아?"},
                    "updated_at": "2026-04-22T00:00:00",
                }
            )

    monkeypatch.setattr(TASK_BROWSER_UI, "_clear_terminal", lambda: None)
    monkeypatch.setattr(TASK_BROWSER_UI.sys.stdout, "isatty", lambda: False)

    TASK_BROWSER_UI.run_tasks_browser(
        FakeClient(),
        settings,
        input_func=lambda prompt="": next(commands),
        output_func=outputs.append,
    )

    assert any("Tasks > 모델 생성 요청" in output for output in outputs)
    assert any("Tasks > 모델 생성 요청 > 모델 응답 생성" in output for output in outputs)
    assert outputs[-1] == "작업 브라우저를 닫을게."


def test_tasks_browser_preview_changes_with_selected_row(monkeypatch):
    monkeypatch.setattr(TASK_BROWSER_UI.sys.stdout, "isatty", lambda: False)
    state = TASK_BROWSER_UI.TaskBrowserState(
        list_payload={
            "items": [
                {
                    "task_run_id": "task_1",
                    "task_type": "stub.echo",
                    "status": "COMPLETED",
                    "title": "첫 번째 작업",
                    "input_summary": "첫 번째 입력",
                    "step_count": 1,
                    "current_step": {"title": "첫 단계", "summary_message": "첫 번째 진행 요약"},
                },
                {
                    "task_run_id": "task_2",
                    "task_type": "model.generate",
                    "status": "RUNNING",
                    "title": "두 번째 작업",
                    "input_summary": "두 번째 입력",
                    "step_count": 2,
                    "current_step": {"title": "둘째 단계", "summary_message": "두 번째 진행 요약"},
                },
            ],
            "page": 1,
            "page_size": 8,
            "total_count": 2,
        },
    )

    first_rendered = TASK_BROWSER_UI.render_tasks_browser_list(state)
    state.selected_index = 1
    second_rendered = TASK_BROWSER_UI.render_tasks_browser_list(state)

    assert "- 제목: 첫 번째 작업" in first_rendered
    assert "- 제목: 두 번째 작업" in second_rendered
    assert "- 현재: 두 번째 진행 요약" in second_rendered


def test_tasks_browser_detail_body_left_right_do_not_move_step(monkeypatch):
    monkeypatch.setattr(TASK_BROWSER_UI.sys.stdout, "isatty", lambda: False)
    state = TASK_BROWSER_UI.TaskBrowserState(
        depth="task_detail",
        detail_task={"title": "승인 대기 태스크"},
        detail_steps=[
            {"step_run_id": "step_1", "step_type": "approval.plan", "title": "승인 조건 정리", "status": "COMPLETED"},
            {"step_run_id": "step_2", "step_type": "approval.wait", "title": "사용자 승인 대기", "status": "WAITING"},
        ],
        selected_step_index=1,
    )

    TASK_BROWSER_UI._handle_task_detail_command(None, get_settings(), state, "left")
    assert state.selected_step_index == 1

    TASK_BROWSER_UI._handle_task_detail_command(None, get_settings(), state, "right")
    assert state.selected_step_index == 1


def test_tasks_browser_list_viewport_follows_selected_row(monkeypatch):
    monkeypatch.setattr(TASK_BROWSER_UI.sys.stdout, "isatty", lambda: False)
    monkeypatch.setattr(TASK_BROWSER_UI.shutil, "get_terminal_size", lambda fallback=(120, 30): os.terminal_size((120, 20)))

    items = []
    for index in range(6):
        items.append(
            {
                "task_run_id": f"task_{index}",
                "task_type": "stub.echo",
                "status": "COMPLETED",
                "title": f"작업 {index}",
                "input_summary": f"입력 {index}",
                "step_count": 1,
                "current_step": {"title": f"step {index}", "summary_message": f"진행 {index}"},
            }
        )

    state = TASK_BROWSER_UI.TaskBrowserState(
        list_payload={"items": items, "page": 1, "page_size": 8, "total_count": len(items)},
        selected_index=5,
    )

    rendered = TASK_BROWSER_UI.render_tasks_browser_list(state)

    assert "Task 목록 (6-6 / 6)" in rendered
    assert "› [6] 작업 5 | COMPLETED | step 1개" in rendered
    assert "… 위에 5개 더 있음" in rendered
    assert "[1] 작업 0" not in rendered


def test_tasks_browser_detail_viewport_follows_selected_step(monkeypatch):
    monkeypatch.setattr(TASK_BROWSER_UI.sys.stdout, "isatty", lambda: False)
    monkeypatch.setattr(TASK_BROWSER_UI.shutil, "get_terminal_size", lambda fallback=(120, 30): os.terminal_size((120, 18)))

    steps = []
    for index in range(8):
        steps.append(
            {
                "step_run_id": f"step_{index}",
                "step_type": "approval.wait",
                "title": f"단계 {index}",
                "status": "WAITING" if index == 7 else "COMPLETED",
                "summary_message": f"요약 {index}",
            }
        )

    state = TASK_BROWSER_UI.TaskBrowserState(
        depth="task_detail",
        detail_task={"title": "승인 대기 태스크"},
        detail_steps=steps,
        selected_step_index=7,
    )

    rendered = TASK_BROWSER_UI.render_task_detail(state)

    assert "Step 목록 (8-8 / 8)" in rendered
    assert "› [현재] 단계 7 | WAITING" in rendered
    assert "… 위에 7개 더 있음" in rendered
    assert "단계 0" not in rendered


def test_initial_login_choice_uses_prompt_toolkit_choice(monkeypatch):
    monkeypatch.setattr(PROMPT_UI, "_supports_windows_console_choice", lambda: False)
    monkeypatch.setattr(PROMPT_UI, "supports_interactive_choice", lambda: True)

    called = {}

    def fake_choice(message, *, options, default, symbol, show_frame, style):
        called["message"] = message
        called["options"] = options
        called["default"] = default
        called["symbol"] = symbol
        return False

    monkeypatch.setattr(PROMPT_UI, "choice", fake_choice)

    assert PROMPT_UI.choose_initial_login_action() is False
    assert called["message"] == "OpenAI 로그인이 필요합니다."
    assert called["options"] == [(True, "1. 로그인"), (False, "2. 취소")]
    assert called["default"] is True
    assert called["symbol"] == "›"


def test_shell_prompt_completion_current_style_is_not_reverse():
    style = PROMPT_UI._shell_prompt_style()
    attrs = style.get_attrs_for_style_str("class:completion-menu.completion.current")

    assert attrs.reverse is False
    assert attrs.bgcolor == "default"


def test_shell_prompt_completion_current_colors_description_too():
    style = PROMPT_UI._shell_prompt_style()
    description_attrs = style.get_attrs_for_style_str("class:completion-menu.completion.current class:completion-description")
    command_attrs = style.get_attrs_for_style_str("class:completion-menu.completion.current class:completion-command")
    normal_description_attrs = style.get_attrs_for_style_str("class:completion-menu.completion class:completion-description")

    assert description_attrs.color == "ffffff"
    assert command_attrs.color == "ffffff"
    assert normal_description_attrs.color == "8a8a8a"


def test_shell_prompt_installs_completion_menu_without_scrollbar(monkeypatch):
    installed = {}

    class FakePromptSession:
        def __init__(self, **kwargs):
            installed["kwargs"] = kwargs

    monkeypatch.setattr(PROMPT_UI, "_supports_prompt_toolkit", lambda: True)
    monkeypatch.setattr(PROMPT_UI, "PromptSession", FakePromptSession)
    monkeypatch.setattr(PROMPT_UI.prompt_shortcuts, "CompletionsMenu", object)

    PROMPT_UI.create_shell_prompt_session("› ")

    assert PROMPT_UI.prompt_shortcuts.CompletionsMenu is PROMPT_UI._NoScrollbarCompletionsMenu
    assert installed["kwargs"]["complete_style"] is PROMPT_UI.CompleteStyle.COLUMN


def test_initial_login_choice_uses_windows_console_arrows(monkeypatch, capsys):
    class FakeMsvcrt:
        def __init__(self):
            self.keys = iter(["\xe0", "P", "\r"])

        def getwch(self):
            return next(self.keys)

    monkeypatch.setattr(PROMPT_UI, "_supports_windows_console_choice", lambda: True)
    monkeypatch.setattr(PROMPT_UI, "msvcrt", FakeMsvcrt())

    assert PROMPT_UI.choose_initial_login_action() is False
    captured = capsys.readouterr().out
    assert "OpenAI 로그인이 필요합니다." in captured
    assert "2. 취소" in captured


def test_remote_client_keeps_origin_base_url_paths():
    client = RemoteCLIClient(base_url="http://127.0.0.1:8000", timeout_seconds=10)

    assert client._normalize_request_path("/api/v1/providers/openai_oauth/auth") == "/api/v1/providers/openai_oauth/auth"


def test_shell_slash_tasks_runs_browser(monkeypatch):
    called = {}
    settings = get_settings()
    parser = build_parser(settings)
    shell_args = parser.parse_args(["shell"])

    def fake_browser(client, settings, *, initial_filter, initial_task_id):
        called["filter"] = initial_filter
        called["task_id"] = initial_task_id

    monkeypatch.setattr(CLI_MAIN_MODULE, "_run_tasks_browser", fake_browser)

    handled = CLI_MAIN_MODULE._handle_shell_slash_command("/tasks waiting", shell_args, settings, object(), parser)

    assert handled is True
    assert called == {"filter": "WAITING", "task_id": None}


def test_cli_tasks_list_local(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-tasks.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))

    main(["--mode", "local", "create-task", "--type", "echo_flow", "--payload", '{"message":"one"}'])
    capsys.readouterr()
    main(["--mode", "local", "create-task", "--type", "approval_wait_flow", "--payload", '{"subject":"two"}'])
    capsys.readouterr()

    exit_code = main(["--mode", "local", "--json", "tasks", "--status", "WAITING"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert '"status_filter": "WAITING"' in captured
    assert '"status": "WAITING"' in captured


def test_cli_create_task_local(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))

    exit_code = main(["--mode", "local", "create-task", "--type", "echo_flow", "--payload", '{"message":"cli"}'])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "[HeyGent CLI] 작업 생성 결과" in captured
    assert '"status": "COMPLETED"' in captured


def test_cli_resume_task_local(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-resume.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))

    create_code = main(["--mode", "local", "create-task", "--type", "approval_wait_flow", "--payload", '{"subject":"demo"}'])
    create_output = capsys.readouterr().out
    task_id = create_output.split('"task_run_id": "')[1].split('"')[0]

    resume_code = main(["--mode", "local", "resume-task", "--task-id", task_id, "--payload", '{"approved": true}'])
    resume_output = capsys.readouterr().out

    assert create_code == 0
    assert resume_code == 0
    assert "[HeyGent CLI] 승인 재개 결과" in resume_output
    assert '"status": "COMPLETED"' in resume_output


def test_cli_create_task_prompt_shortcut(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-prompt.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))

    exit_code = main(["--mode", "local", "create-task", "--type", "model_generate_flow", "--prompt", "한 줄 요약해줘"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert '"flow_name": "model_generate_flow"' in captured
    assert '"status": "COMPLETED"' in captured


def test_cli_list_commands_local(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-list.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))

    flow_code = main(["--mode", "local", "list-flows"])
    flow_output = capsys.readouterr().out
    provider_code = main(["--mode", "local", "list-providers"])
    provider_output = capsys.readouterr().out

    assert flow_code == 0
    assert provider_code == 0
    assert "[HeyGent CLI] 플로우 목록 결과" in flow_output
    assert "model_generate_flow" in flow_output
    assert "[HeyGent CLI] 프로바이더 목록" in provider_output
    assert "OpenAI Status" in provider_output
    assert "openai_oauth" in provider_output


def test_cli_health_local(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-health.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))

    exit_code = main(["--mode", "local", "health"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "[HeyGent CLI] 서버 상태 확인 결과" in captured
    assert '"status": "ready"' in captured


def test_cli_status_local(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-status.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))

    exit_code = main(["--mode", "local", "status"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "[HeyGent CLI] 연결 상태" in captured
    assert "OpenAI Status" in captured
    assert "connected:" in captured


def test_cli_provider_auth_local(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-provider-auth.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))

    exit_code = main(["--mode", "local", "provider-auth", "--provider", "openai_oauth"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "[HeyGent CLI] 프로바이더 인증 시작 결과" in captured
    assert '"status": "authorization_required"' in captured


def test_cli_openai_onboarding_local(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-onboard.db"
    auth_path = tmp_path / "auth.json"
    auth_path.write_text(
        json.dumps(
            {
                "auth_mode": "chatgpt",
                "tokens": {
                    "access_token": _make_test_access_token(),
                    "refresh_token": "refresh-test",
                    "account_id": "acct_test",
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))
    monkeypatch.setenv("HEYGENT_OPENAI_AUTH_FILE", str(auth_path))

    exit_code = main(["--mode", "local", "onboard-openai", "--allow-local-auth-fallback", "--no-run-check"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "[HeyGent CLI] OpenAI 연결" in captured
    assert "이미 OpenAI 연결이 준비되어 있습니다." in captured
    assert "OpenAI Status" in captured
    assert "connected:" in captured


def test_cli_openai_onboarding_remote_one_click(monkeypatch, capsys):
    fake_client = FakeRemoteClient(
        [
            FakeResponse(
                {
                    "provider_name": "openai_oauth",
                    "status": "authorization_required",
                    "detail": "go",
                    "authorization_url": "https://auth.openai.test/start",
                    "redirect_uri": "http://localhost:1455/auth/callback",
                    "scopes": ["openid", "profile", "email", "offline_access"],
                    "state": "state_123",
                    "missing_env": [],
                    "metadata": {"pkce_required": True},
                }
            ),
            FakeResponse(
                {
                    "provider_name": "openai_oauth",
                    "status": "connected",
                    "connected": True,
                    "detail": "done",
                    "scopes": ["openid", "profile", "email", "offline_access"],
                    "expires_at": "2099-01-01T00:00:00+00:00",
                    "metadata": {"account_id": "acct_test"},
                }
            ),
            FakeResponse(
                {
                    "provider_name": "openai_oauth",
                    "healthy": True,
                    "configured": True,
                    "connected": True,
                    "auth_type": "oauth",
                    "detail": "connected",
                    "missing_env": [],
                    "scopes": ["openid", "profile", "email", "offline_access"],
                    "expires_at": "2099-01-01T00:00:00+00:00",
                }
            ),
            FakeResponse(
                {
                    "task_run_id": "task_test",
                    "task_type": "model.generate",
                    "flow_name": "model_generate_flow",
                    "status": "COMPLETED",
                    "input_payload": {"prompt": "테스트"},
                    "result_payload": {"provider_name": "openai_oauth", "text": "연결 확인 완료", "metadata": {"mode": "live"}},
                    "wait_payload": {},
                    "error_message": None,
                    "progress_summary": "done",
                    "revision": 1,
                }
            ),
        ]
    )

    class FakeListener:
        def wait(self, timeout, *, poll_interval=0.2):
            return {"ok": True, "payload": fake_client.request("POST", "/api/v1/providers/openai_oauth/callback").json()}

        def close(self):
            return None

    monkeypatch.setattr("builtins.input", lambda prompt="": "YES")
    monkeypatch.setattr(CLI_MAIN_MODULE, "_build_transport", lambda args: fake_client)
    monkeypatch.setattr(CLI_MAIN_MODULE, "_open_browser", lambda url: True)
    monkeypatch.setattr(CLI_MAIN_MODULE, "_start_local_oauth_callback_listener", lambda *args, **kwargs: FakeListener())

    exit_code = main(["onboard-openai", "--wait-seconds", "1", "--check-prompt", "테스트"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "OpenAI 연결이 필요합니다." in captured
    assert "Login URL" in captured
    assert "Waiting for authentication..." in captured
    assert "Connected ✓" in captured
    assert "온보딩 완료. 이제 바로 사용할 수 있어." in captured


def test_cli_openai_onboarding_ctrl_c_while_waiting(monkeypatch, capsys):
    fake_client = FakeRemoteClient(
        [
            FakeResponse(
                {
                    "provider_name": "openai_oauth",
                    "status": "authorization_required",
                    "detail": "go",
                    "authorization_url": "https://auth.openai.test/start",
                    "redirect_uri": "http://localhost:1455/auth/callback",
                    "scopes": ["openid"],
                    "state": "state_123",
                    "missing_env": [],
                    "metadata": {"pkce_required": True},
                }
            )
        ]
    )

    class InterruptingListener:
        closed = False

        def wait(self, timeout, *, poll_interval=0.2):
            raise KeyboardInterrupt

        def close(self):
            self.closed = True

    listener = InterruptingListener()
    monkeypatch.setattr(CLI_MAIN_MODULE, "_build_transport", lambda args: fake_client)
    monkeypatch.setattr(CLI_MAIN_MODULE, "_open_browser", lambda url: True)
    monkeypatch.setattr(CLI_MAIN_MODULE, "_start_local_oauth_callback_listener", lambda *args, **kwargs: listener)

    exit_code = main(["onboard-openai", "--yes", "--wait-seconds", "120"])
    captured = capsys.readouterr().out

    assert exit_code == 130
    assert listener.closed is True
    assert "Waiting for authentication..." in captured
    assert "로그인을 취소하고 종료할게." in captured


def test_cli_provider_refresh_local(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-refresh.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))

    exit_code = main(["--mode", "local", "provider-refresh", "--provider", "openai_oauth"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "[HeyGent CLI] 프로바이더 연결 갱신 결과" in captured
    assert '"status": "reconnect_required"' in captured or '"status": "not_connected"' in captured


def test_cli_provider_disconnect_local(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-disconnect.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))

    exit_code = main(["--mode", "local", "provider-disconnect", "--provider", "openai_oauth"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "[HeyGent CLI] 프로바이더 연결 해제 결과" in captured
    assert '"status": "disconnected"' in captured


def test_cli_help_text_is_korean():
    parser = build_parser(get_settings())
    help_text = parser.format_help()

    assert "한글 CLI" in help_text
    assert "shell" in help_text
    assert "/help" in help_text
    assert "status" in help_text
    assert "serve" in help_text
    assert "onboard-openai" in help_text
    assert "provider-refresh" in help_text
    assert "provider-disconnect" in help_text
    assert "예시:" in help_text


def test_cli_shell_default_mode(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-shell-default.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))
    answers = iter(["2", "/", "/status", "안녕", "/exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))

    exit_code = main(["--mode", "local"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "OpenAI 로그인이 필요합니다." in captured
    assert "› HeyGent AI" in captured
    assert "not connected  /auth to sign in" in captured
    assert "[HeyGent CLI] 연결 상태" in captured
    assert "› 안녕" in captured
    assert "mode:" in captured
    assert "• " in captured
    assert "셸을 종료할게." in captured


def test_cli_shell_interrupt(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-shell-interrupt.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))
    answers = iter(["2", "안녕", "/exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))

    def fake_prompt_task(args, settings, prompt):
        time.sleep(0.3)
        return FakeResponse(
            {
                "task_run_id": "task_interrupt",
                "task_type": "model.generate",
                "flow_name": "model_generate_flow",
                "status": "COMPLETED",
                "input_payload": {"prompt": prompt},
                "result_payload": {"provider_name": "openai_oauth", "text": "늦게 도착한 응답", "metadata": {"mode": "live", "model": "gpt-5.4"}},
                "wait_payload": {},
                "error_message": None,
                "progress_summary": "done",
                "revision": 1,
            }
        )

    interrupt_calls = iter([True])
    monkeypatch.setattr(CLI_MAIN_MODULE, "_run_prompt_task_with_fresh_transport", fake_prompt_task)
    monkeypatch.setattr(CLI_MAIN_MODULE, "_shell_interrupt_requested", lambda: next(interrupt_calls, False))

    exit_code = main(["--mode", "local"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "Working (" in captured
    assert "취소했어. 요청은 백그라운드에서 끝날 수 있어." in captured
    assert "셸을 종료할게." in captured


def test_cli_shell_auth_asks_before_reconnect(monkeypatch, capsys):
    fake_client = FakeRemoteClient(
        [
            FakeResponse(
                {
                    "provider_name": "openai_oauth",
                    "healthy": True,
                    "configured": True,
                    "connected": True,
                    "auth_type": "oauth",
                    "detail": "connected",
                    "missing_env": [],
                    "scopes": ["openid"],
                    "expires_at": "2099-01-01T00:00:00+00:00",
                }
            ),
            FakeResponse(
                {
                    "provider_name": "openai_oauth",
                    "healthy": True,
                    "configured": True,
                    "connected": True,
                    "auth_type": "oauth",
                    "detail": "connected",
                    "missing_env": [],
                    "scopes": ["openid"],
                    "expires_at": "2099-01-01T00:00:00+00:00",
                }
            ),
        ]
    )
    answers = iter(["/auth", "no", "/exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    monkeypatch.setattr(CLI_MAIN_MODULE, "_build_transport", lambda args: fake_client)

    def fail_onboarding(*args, **kwargs):
        raise AssertionError("onboarding should not start when reconnect is declined")

    monkeypatch.setattr(CLI_MAIN_MODULE, "_handle_openai_onboarding", fail_onboarding)

    exit_code = main(["--base-url", "http://127.0.0.1:8000/api/v1"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "이미 OpenAI 연결이 저장되어 있어." in captured
    assert "재연결을 취소했어. 입력창으로 돌아갈게." in captured
    assert "셸을 종료할게." in captured


def test_cli_shell_slash_command_interrupt_returns_to_prompt(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-slash-interrupt.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))
    answers = iter(["2", "/auth", "/exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))

    def fake_slash_command(raw, shell_args, settings, client, parser):
        if raw == "/auth":
            raise KeyboardInterrupt
        return False

    monkeypatch.setattr(CLI_MAIN_MODULE, "_handle_shell_slash_command", fake_slash_command)

    exit_code = main(["--mode", "local"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "취소했어. 입력창으로 돌아갈게." in captured


def test_cli_shell_initial_login_runs_before_banner(monkeypatch, capsys):
    fake_client = FakeRemoteClient(
        [
            FakeResponse(
                {
                    "provider_name": "openai_oauth",
                    "healthy": True,
                    "configured": True,
                    "connected": False,
                    "auth_type": "oauth",
                    "detail": "not connected",
                    "missing_env": [],
                    "scopes": ["openid"],
                    "expires_at": None,
                }
            ),
            FakeResponse({"provider_name": "openai_oauth", "status": "connected", "connected": True, "detail": "done", "expires_at": "2099-01-01T00:00:00+00:00"}),
            FakeResponse(
                {
                    "provider_name": "openai_oauth",
                    "healthy": True,
                    "configured": True,
                    "connected": True,
                    "auth_type": "oauth",
                    "detail": "connected",
                    "missing_env": [],
                    "scopes": ["openid"],
                    "expires_at": "2099-01-01T00:00:00+00:00",
                }
            ),
            FakeResponse(
                {
                    "provider_name": "openai_oauth",
                    "healthy": True,
                    "configured": True,
                    "connected": True,
                    "auth_type": "oauth",
                    "detail": "connected",
                    "missing_env": [],
                    "scopes": ["openid"],
                    "expires_at": "2099-01-01T00:00:00+00:00",
                }
            ),
        ]
    )
    answers = iter(["1", "/exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    monkeypatch.setattr(CLI_MAIN_MODULE, "_build_transport", lambda args: fake_client)

    exit_code = main(["--base-url", "http://127.0.0.1:8000/api/v1"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert captured.index("OpenAI 로그인이 필요합니다.") < captured.index("› HeyGent AI")
    assert "auth:      connected  /status to view" in captured
    assert "셸을 종료할게." in captured


def test_cli_shell_initial_login_ctrl_c_exits(monkeypatch, capsys):
    fake_client = FakeRemoteClient(
        [
            FakeResponse(
                {
                    "provider_name": "openai_oauth",
                    "healthy": True,
                    "configured": True,
                    "connected": False,
                    "auth_type": "oauth",
                    "detail": "not connected",
                    "missing_env": [],
                    "scopes": ["openid"],
                    "expires_at": None,
                }
            )
        ]
    )

    def raise_keyboard_interrupt(prompt=""):
        raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", raise_keyboard_interrupt)
    monkeypatch.setattr(CLI_MAIN_MODULE, "_build_transport", lambda args: fake_client)
    monkeypatch.setattr(PROMPT_UI, "_supports_windows_console_choice", lambda: False)
    monkeypatch.setattr(PROMPT_UI, "supports_interactive_choice", lambda: False)

    exit_code = main(["--base-url", "http://127.0.0.1:8000/api/v1"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "셸을 종료할게." in captured
    assert "› HeyGent AI" not in captured


def test_cli_shell_initial_login_wait_cancel_exits_without_banner(monkeypatch, capsys):
    fake_client = FakeRemoteClient(
        [
            FakeResponse(
                {
                    "provider_name": "openai_oauth",
                    "healthy": True,
                    "configured": True,
                    "connected": False,
                    "auth_type": "oauth",
                    "detail": "not connected",
                    "missing_env": [],
                    "scopes": ["openid"],
                    "expires_at": None,
                }
            )
        ]
    )

    monkeypatch.setattr("builtins.input", lambda prompt="": "1")
    monkeypatch.setattr(CLI_MAIN_MODULE, "_build_transport", lambda args: fake_client)
    monkeypatch.setattr(CLI_MAIN_MODULE, "_run_shell_auth", lambda args, settings, client: 130)
    monkeypatch.setattr(PROMPT_UI, "_supports_windows_console_choice", lambda: False)
    monkeypatch.setattr(PROMPT_UI, "supports_interactive_choice", lambda: False)

    exit_code = main(["--base-url", "http://127.0.0.1:8000/api/v1"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "셸을 종료할게." in captured
    assert "› HeyGent AI" not in captured


def test_cli_slash_help(capsys):
    exit_code = main(["/help"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "[HeyGent CLI] 전체 도움말" in captured
    assert "create-task" in captured


def test_cli_slash_status(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli-slash-status.db"
    monkeypatch.setenv("HEYGENT_AI_DB_PATH", str(db_path))

    exit_code = main(["--mode", "local", "/status"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "[HeyGent CLI] 연결 상태" in captured
    assert "OpenAI Status" in captured


def test_cli_command_help(capsys):
    exit_code = main(["help", "create-task"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "[HeyGent CLI] create-task 도움말" in captured
    assert "--type" in captured
