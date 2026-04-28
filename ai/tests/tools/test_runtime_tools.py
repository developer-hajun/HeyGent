import json
import sys

from app.domain.orchestration.runtime_planning.todo_state import (
    apply_tool_results_to_todo_state,
    build_task_todo_payload,
)
from app.tools.file import file_tools
from app.tools.runtime.local_tool_runtime import LocalToolRuntime
from app.tools.runtime.toolsets import resolve_runtime_tool_names


class DummySessionStore:
    pass


def test_runtime_exposes_todo_schema_without_legacy_write_name():
    runtime = LocalToolRuntime(skill_registry=object(), session_store=DummySessionStore())

    definitions = runtime.list_tool_definitions(enabled_toolsets=("planning",))

    schema_by_name = {definition["name"]: definition["schema"] for definition in definitions}
    assert [definition["name"] for definition in definitions] == ["step", "todo"]
    assert schema_by_name["todo"]["name"] == "todo"
    assert "todos" in schema_by_name["todo"]["parameters"]["properties"]
    assert schema_by_name["step"]["name"] == "step"
    assert "steps" in schema_by_name["step"]["parameters"]["properties"]
    title_description = schema_by_name["step"]["parameters"]["properties"]["steps"]["items"]["properties"]["title"]["description"]
    assert "target/topic/artifact" in title_description
    assert "기존 자료 파악" in title_description


def test_runtime_exposes_terminal_argument_schema():
    runtime = LocalToolRuntime(skill_registry=object(), session_store=DummySessionStore())

    definitions = runtime.list_tool_definitions(enabled_toolsets=("terminal",))
    terminal_schema = next(item["schema"] for item in definitions if item["name"] == "terminal.run")

    properties = terminal_schema["parameters"]["properties"]
    assert "command" in properties
    assert "argv" in properties
    assert "Provide at least one" in terminal_schema["description"]


def test_runtime_exposes_file_tool_definitions_from_file_tool_module():
    runtime = LocalToolRuntime(skill_registry=object(), session_store=DummySessionStore())

    definitions = runtime.list_tool_definitions(enabled_toolsets=("file",))

    assert [definition["name"] for definition in definitions] == [
        "patch",
        "read_file",
        "search_files",
        "write_file",
    ]
    schema_by_name = {definition["name"]: definition["schema"] for definition in definitions}
    assert schema_by_name["read_file"]["parameters"]["properties"]["path"]["type"] == "string"
    assert schema_by_name["write_file"]["parameters"]["properties"]["content"]["type"] == "string"
    assert schema_by_name["search_files"]["parameters"]["properties"]["query"]["type"] == "string"


def test_file_toolset_is_available_for_coding_and_local_core_but_not_safe():
    file_tool_names = {"read_file", "write_file", "patch", "search_files"}

    assert file_tool_names <= resolve_runtime_tool_names(("file",))
    assert file_tool_names <= resolve_runtime_tool_names(("coding",))
    assert file_tool_names <= resolve_runtime_tool_names(("local-core",))
    assert file_tool_names.isdisjoint(resolve_runtime_tool_names(("safe",)))


def test_todo_writes_and_reads_full_json_ready_result():
    runtime = LocalToolRuntime(skill_registry=object(), session_store=DummySessionStore())

    written = runtime.run_call(
        name="todo",
        args={
            "todos": [
                {"id": "plan", "content": "계획 정리", "status": "completed"},
                {"id": "ship", "content": "배포 점검", "status": "pending"},
            ]
        },
    )
    read = runtime.run_call(name="todo", args={})

    assert written == read
    assert written["todos"] == [
        {"id": "plan", "content": "계획 정리", "status": "completed"},
        {"id": "ship", "content": "배포 점검", "status": "pending"},
    ]
    assert written["summary"] == {
        "total": 2,
        "pending": 1,
        "in_progress": 0,
        "completed": 1,
        "cancelled": 0,
    }
    json.dumps(written, ensure_ascii=False)


def test_step_writes_and_reads_declared_semantic_steps():
    runtime = LocalToolRuntime(skill_registry=object(), session_store=DummySessionStore())

    written = runtime.run_call(
        name="step",
        args={
            "steps": [
                {
                    "id": "research",
                    "title": "뉴스 근거 자료 조사",
                    "summary": "뉴스 근거 자료 조사 중",
                    "goal": "근거 자료를 정리한다.",
                    "status": "completed",
                },
                {
                    "id": "draft",
                    "title": "뉴스 브리핑 문서 초안 작성",
                    "summary": "뉴스 브리핑 문서 초안 작성 중",
                    "goal": "조사 결과를 문서화한다.",
                    "status": "in_progress",
                },
            ]
        },
    )
    read = runtime.run_call(name="step", args={"steps": [], "merge": True})

    assert written == read
    assert written["steps"] == [
        {
            "id": "research",
            "title": "뉴스 근거 자료 조사",
            "summary": "뉴스 근거 자료 조사 중",
            "goal": "근거 자료를 정리한다.",
            "status": "completed",
        },
        {
            "id": "draft",
            "title": "뉴스 브리핑 문서 초안 작성",
            "summary": "뉴스 브리핑 문서 초안 작성 중",
            "goal": "조사 결과를 문서화한다.",
            "status": "in_progress",
        },
    ]


def test_todo_projection_accepts_json_string_tool_content():
    state = apply_tool_results_to_todo_state(
        {},
        [
            {
                "name": "todo",
                "args": {},
                "result": json.dumps(
                    {
                        "todos": [{"id": "ship", "content": "배포 점검", "status": "pending"}],
                        "summary": {"total": 1, "pending": 1},
                    },
                    ensure_ascii=False,
                ),
            }
        ],
    )

    assert build_task_todo_payload(state)["items"] == [
        {
            "id": "ship",
            "key": "ship",
            "content": "배포 점검",
            "title": "배포 점검",
            "kind": "todo",
            "status": "pending",
        }
    ]


def test_runtime_rejects_unknown_or_disabled_tool_before_execution():
    runtime = LocalToolRuntime(skill_registry=object(), session_store=DummySessionStore())

    unknown = runtime.run_call(name="missing.tool", args={})
    disabled = runtime.run_call(
        name="terminal.run",
        args={"command": "exit 13"},
        enabled_toolsets=("planning",),
    )

    assert unknown["ok"] is False
    assert unknown["error"]["code"] == "tool_unavailable"
    assert disabled["ok"] is False
    assert disabled["error"]["code"] == "tool_unavailable"
    assert json.loads(disabled["content"])["error"]["tool_name"] == "terminal.run"


def test_runtime_rejects_invalid_arguments_as_tool_result():
    runtime = LocalToolRuntime(skill_registry=object(), session_store=DummySessionStore())

    result = runtime.run_call(name="todo", args={"todos": [{"id": "plan"}]})

    assert result["ok"] is False
    assert result["error"]["code"] == "invalid_tool_arguments"
    assert "todos.0.content" in result["error"]["message"]


def test_file_runtime_calls_file_module_handler(monkeypatch):
    def fake_read_file_handler(args):
        return {"ok": True, "path": args["path"], "content": "runtime file content"}

    monkeypatch.setattr(file_tools, "read_file_handler", fake_read_file_handler, raising=False)
    runtime = LocalToolRuntime(skill_registry=object(), session_store=DummySessionStore())

    result = runtime.run_call(
        name="read_file",
        args={"path": "README.md"},
        enabled_toolsets=("file",),
    )

    assert result == {"ok": True, "path": "README.md", "content": "runtime file content"}


def test_file_runtime_blocks_write_when_only_safe_toolset_enabled(monkeypatch):
    called = False

    def fake_write_file_handler(args):
        nonlocal called
        called = True
        return {"ok": True}

    monkeypatch.setattr(file_tools, "write_file_handler", fake_write_file_handler, raising=False)
    runtime = LocalToolRuntime(skill_registry=object(), session_store=DummySessionStore())

    result = runtime.run_call(
        name="write_file",
        args={"path": "README.md", "content": "blocked"},
        enabled_toolsets=("safe",),
    )

    assert called is False
    assert result["ok"] is False
    assert result["error"]["code"] == "tool_unavailable"
    assert result["error"]["tool_name"] == "write_file"


def test_terminal_runtime_treats_empty_cwd_as_current_directory():
    runtime = LocalToolRuntime(skill_registry=object(), session_store=DummySessionStore())

    result = runtime.run_call(name="terminal.run", args={"command": "echo RUNTIME_OK", "cwd": ""})

    assert result["returncode"] == 0
    assert "RUNTIME_OK" in result["stdout"]


def test_runtime_file_tool_ignores_model_supplied_workspace_root(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    (outside / "secret.txt").write_text("outside-secret", encoding="utf-8")
    monkeypatch.chdir(workspace)
    runtime = LocalToolRuntime(skill_registry=object(), session_store=DummySessionStore())

    result = runtime.run_call(
        name="read_file",
        args={"workspace_root": str(outside), "path": str(outside / "secret.txt")},
        enabled_toolsets=("file",),
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "tool_execution_failed"
    assert "PermissionError" in result["error"]["message"]
    assert "outside-secret" not in json.dumps(result, ensure_ascii=False)


def test_terminal_runtime_caps_large_stdout():
    runtime = LocalToolRuntime(skill_registry=object(), session_store=DummySessionStore())

    result = runtime.run_call(
        name="terminal.run",
        args={"argv": [sys.executable, "-c", "print('x' * 20000)"]},
        enabled_toolsets=("terminal",),
    )

    assert result["returncode"] == 0
    assert result["stdout_truncated"] is True
    assert "[truncated" in result["stdout"]
    assert len(result["stdout"]) < 20000


def test_terminal_runtime_blocks_dangerous_shell_command_before_execution(tmp_path):
    runtime = LocalToolRuntime(skill_registry=object(), session_store=DummySessionStore())

    blocked_commands = [
        "git reset --hard",
        "rm -rf .",
        "Remove-Item . -Force -Recurse",
        "Remove-Item . -Recurse -Force",
    ]

    for command in blocked_commands:
        result = runtime.run_call(
            name="terminal.run",
            args={"command": command, "cwd": str(tmp_path)},
            enabled_toolsets=("terminal",),
        )

        assert result["ok"] is False
        assert result["error"]["code"] == "blocked_command"
        assert result["returncode"] is None
