import json

from app.domain.orchestration.runtime_planning.todo_state import (
    apply_tool_results_to_todo_state,
    build_task_todo_payload,
)
from app.tools.runtime.local_tool_runtime import LocalToolRuntime


class DummySessionStore:
    pass


def test_runtime_exposes_todo_schema_without_legacy_write_name():
    runtime = LocalToolRuntime(skill_registry=object(), session_store=DummySessionStore())

    definitions = runtime.list_tool_definitions(enabled_toolsets=("planning",))

    assert [definition["name"] for definition in definitions] == ["todo"]
    assert definitions[0]["schema"]["name"] == "todo"
    assert "todos" in definitions[0]["schema"]["parameters"]["properties"]


def test_runtime_exposes_terminal_argument_schema():
    runtime = LocalToolRuntime(skill_registry=object(), session_store=DummySessionStore())

    definitions = runtime.list_tool_definitions(enabled_toolsets=("terminal",))
    terminal_schema = next(item["schema"] for item in definitions if item["name"] == "terminal.run")

    properties = terminal_schema["parameters"]["properties"]
    assert "command" in properties
    assert "argv" in properties
    assert "Provide at least one" in terminal_schema["description"]


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


def test_terminal_runtime_treats_empty_cwd_as_current_directory():
    runtime = LocalToolRuntime(skill_registry=object(), session_store=DummySessionStore())

    result = runtime.run_call(name="terminal.run", args={"command": "echo RUNTIME_OK", "cwd": ""})

    assert result["returncode"] == 0
    assert "RUNTIME_OK" in result["stdout"]
