from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import sys

from app.domain.providers.model.base import AgentMessage, AgentModelResponse, AssistantToolCall


def _response(*, text: str = "", tool_calls: list[AssistantToolCall] | None = None, model: str = "gpt-test") -> AgentModelResponse:
    calls = tool_calls or []
    return AgentModelResponse(
        provider_name="openai_api",
        model=model,
        message=AgentMessage(role="assistant", content=text, tool_calls=calls),
        output_text=text,
        tool_calls=calls,
        finish_reason="tool_calls" if calls else "stop",
        metadata={"model": model},
    )


def _tool_call(call_id: str, name: str, arguments: dict) -> AssistantToolCall:
    return AssistantToolCall(id=call_id, name=name, arguments=arguments)


def _patch_respond(monkeypatch, responses: list[AgentModelResponse | Exception]) -> list[dict]:
    iterator = iter(responses)
    calls: list[dict] = []

    def fake_respond(self, messages, tools, model, tool_choice=None):
        calls.append({"messages": messages, "tools": tools, "model": model, "tool_choice": tool_choice})
        next_response = next(iterator)
        if isinstance(next_response, Exception):
            raise next_response
        return next_response

    monkeypatch.setattr("app.domain.providers.model.openai_api.OpenAIAPIProvider.respond", fake_respond)
    monkeypatch.setattr("app.domain.providers.model.openai_oauth.OpenAIOAuthProvider.respond", fake_respond)
    return calls


def test_agent_loop_executes_native_tool_calls_and_materializes_step(client, monkeypatch):
    provider_calls = _patch_respond(
        monkeypatch,
        [
            _response(
                tool_calls=[
                    _tool_call("call_skills", "skills_list", {}),
                    _tool_call(
                        "call_todo",
                        "todo",
                        {
                            "todos": [
                                {"id": "plan", "content": "계획 정리", "status": "completed"},
                                {"id": "ship", "content": "배포 점검", "status": "pending"},
                            ]
                        },
                    ),
                    _tool_call("call_terminal", "terminal_run", {"argv": [sys.executable, "-c", "print('TOOL_OK')"]}),
                ]
            ),
            _response(text="NATIVE_LOOP_DONE"),
        ],
    )

    response = client.post(
        "/api/v1/taskRuns",
        json={
            "intent_type": "agent.loop",
            "owner_key": "tool-user",
            "session_key": "sess_native_loop",
            "input_payload": {"prompt": "필요하면 도구를 사용해 정리해줘.", "model": "gpt-test"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["entry_executor_key"] == "agent.loop"
    assert body["result_payload"]["text"] == "NATIVE_LOOP_DONE"
    assert [item["name"] for item in body["result_payload"]["tool_results"]] == ["skills.list", "todo", "terminal.run"]
    assert body["todo_state"]["currentKey"] is None
    exposed_tool_names = [tool["function"]["name"] for tool in provider_calls[0]["tools"]]
    assert "skills_list" in exposed_tool_names
    assert "terminal_run" in exposed_tool_names
    assert all("." not in name for name in exposed_tool_names)

    steps = client.get(f"/api/v1/taskRuns/{body['task_run_id']}/steps").json()
    assert len(steps) == 1
    assert steps[0]["input_payload"].get("todo_key") is None
    assert steps[0]["status"] == "COMPLETED"
    todo_items = steps[0]["detail_json"]["planningDetail"]["todoItems"]
    assert [item["key"] for item in todo_items] == ["plan", "ship"]
    assert [item["status"] for item in todo_items] == ["completed", "cancelled"]

    transcript_session = client.app.state.session_store.get_latest_session_by_key("sess_native_loop")
    transcript = client.app.state.session_store.list_messages(transcript_session["id"])
    assert [message["role"] for message in transcript] == ["user", "assistant", "tool", "tool", "tool", "assistant"]
    assert transcript[1]["tool_calls"][0]["id"] == "call_skills"
    assert transcript[2]["tool_call_id"] == "call_skills"


def test_agent_loop_declared_steps_materialize_multiple_stepruns(client, monkeypatch):
    provider_calls = _patch_respond(
        monkeypatch,
        [
            _response(
                tool_calls=[
                    _tool_call(
                        "call_step",
                        "step",
                        {
                            "steps": [
                                    {
                                        "id": "research",
                                        "title": "뉴스 근거 자료 조사",
                                        "summary": "뉴스 근거 자료 조사 중",
                                        "goal": "요청과 관련된 근거 자료를 모은다.",
                                        "status": "completed",
                                    },
                                    {
                                        "id": "draft",
                                        "title": "뉴스 브리핑 문서 초안 작성",
                                        "summary": "뉴스 브리핑 문서 초안 작성 중",
                                        "goal": "조사 결과를 사용자가 읽을 문서로 구성한다.",
                                        "status": "completed",
                                    },
                                    {
                                        "id": "review",
                                        "title": "뉴스 브리핑 결과 검토",
                                        "summary": "뉴스 브리핑 결과 검토 중",
                                        "goal": "빠진 항목과 전달 형식을 점검한다.",
                                        "status": "in_progress",
                                    },
                            ]
                        },
                    )
                ]
            ),
            _response(text="DECLARED_STEPS_DONE"),
        ],
    )

    response = client.post(
        "/api/v1/taskRuns",
        json={
            "intent_type": "agent.loop",
            "owner_key": "declared-step-user",
            "input_payload": {"prompt": "자료 조사하고 문서 초안까지 정리해줘.", "model": "gpt-test"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["progress_summary"] == "뉴스 브리핑 결과 검토 중"

    exposed_tool_names = [tool["function"]["name"] for tool in provider_calls[0]["tools"]]
    assert "step" in exposed_tool_names

    steps = client.get(f"/api/v1/taskRuns/{body['task_run_id']}/steps").json()
    assert len(steps) == 3
    assert [step["title"] for step in steps] == ["뉴스 근거 자료 조사", "뉴스 브리핑 문서 초안 작성", "뉴스 브리핑 결과 검토"]
    assert [step["summary_message"] for step in steps] == ["뉴스 근거 자료 조사 중", "뉴스 브리핑 문서 초안 작성 중", "뉴스 브리핑 결과 검토 중"]
    assert [step["input_payload"].get("observed_step_key") for step in steps] == ["research", "draft", "review"]
    assert [step["semantic"]["key"] for step in steps] == ["observed.research", "observed.draft", "observed.review"]
    assert all(step["input_payload"].get("todo_key") is None for step in steps)
    assert all(step["status"] == "COMPLETED" for step in steps)


def test_agent_loop_provider_timeout_fails_task_and_materializes_failed_step(client, monkeypatch):
    _patch_respond(monkeypatch, [TimeoutError("provider read timeout")])

    response = client.post(
        "/api/v1/taskRuns",
        json={
            "intent_type": "agent.loop",
            "owner_key": "timeout-user",
            "input_payload": {"prompt": "provider timeout을 실패로 저장해줘.", "model": "gpt-test"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "FAILED"
    assert body["error_message"] == "TimeoutError: provider read timeout"
    assert body["progress_summary"] == "작업 처리 중 오류가 발생했습니다."
    assert body["current_step_run_id"]

    steps = client.get(f"/api/v1/taskRuns/{body['task_run_id']}/steps").json()
    assert len(steps) == 1
    assert steps[0]["step_run_id"] == body["current_step_run_id"]
    assert steps[0]["status"] == "FAILED"
    assert steps[0]["error_message"] == "TimeoutError: provider read timeout"
    assert steps[0]["summary_message"] == "작업 처리 중 오류가 발생했습니다."
    operations = steps[0]["detail_json"]["operationDetail"]["operations"]
    assert operations[-1]["key"] == "executor.failure"
    assert operations[-1]["status"] == "failed"
    assert operations[-1]["summary"] == "TimeoutError: provider read timeout"


def test_agent_loop_explicit_task_plan_continues_across_plan_step_anchors(client, monkeypatch):
    _patch_respond(
        monkeypatch,
        [
            _response(text="ANALYZE_DONE"),
            _response(text="WRITE_DONE"),
            _response(text="SHARE_DONE"),
        ],
    )

    response = client.post(
        "/api/v1/taskRuns",
        json={
            "intent_type": "agent.loop",
            "owner_key": "explicit-plan-user",
            "input_payload": {
                "prompt": "명시 계획을 순서대로 처리해줘.",
                "task_plan": {
                    "title": "명시 계획 실행",
                    "steps": [
                        {"key": "analyze", "title": "요청 분석", "goal": "요청을 분석한다."},
                        {"key": "write", "title": "초안 작성", "goal": "초안을 작성한다."},
                        {"key": "share", "title": "결과 공유", "goal": "결과를 공유한다."},
                    ],
                },
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["result_payload"]["text"] == "SHARE_DONE"

    steps = client.get(f"/api/v1/taskRuns/{body['task_run_id']}/steps").json()
    assert len(steps) == 3
    assert [step["input_payload"].get("plan_step_key") for step in steps] == ["analyze", "write", "share"]
    assert [step["input_payload"].get("plan_step_title") for step in steps] == ["요청 분석", "초안 작성", "결과 공유"]
    assert all(step["input_payload"].get("todo_key") is None for step in steps)


def test_agent_loop_uses_input_workspace_root_for_file_and_terminal_runtime(client, monkeypatch, tmp_path):
    workspace = tmp_path / "request-workspace"
    workspace.mkdir()
    file_name = f"request-root-{tmp_path.name}.txt"
    requested_file = workspace / "drafts" / file_name
    server_cwd_file = Path.cwd() / "drafts" / file_name
    server_cwd_terminal_marker = Path.cwd() / "terminal-marker.txt"
    if server_cwd_file.exists():
        server_cwd_file.unlink()
    if server_cwd_terminal_marker.exists():
        server_cwd_terminal_marker.unlink()
    provider_calls = _patch_respond(
        monkeypatch,
        [
            _response(
                tool_calls=[
                    _tool_call(
                        "call_write",
                        "write_file",
                        {
                            "workspace_root": str(Path.cwd()),
                            "path": f"drafts/{file_name}",
                            "content": "request workspace file\n",
                        },
                    ),
                    _tool_call(
                        "call_terminal",
                        "terminal_run",
                        {"argv": [sys.executable, "-c", "import pathlib; pathlib.Path('terminal-marker.txt').write_text('ok')"]},
                    ),
                ]
            ),
            _response(text="WORKSPACE_ROOT_DONE"),
        ],
    )

    response = client.post(
        "/api/v1/taskRuns",
        json={
            "intent_type": "agent.loop",
            "owner_key": "workspace-root-user",
            "input_payload": {
                "prompt": "요청 workspace에서 파일과 터미널 작업을 실행해줘.",
                "workspace_root": str(workspace),
                "enabled_toolsets": ["file", "terminal"],
            },
        },
    )
    server_cwd_created = server_cwd_file.exists()
    if server_cwd_created:
        server_cwd_file.unlink()
    server_cwd_terminal_created = server_cwd_terminal_marker.exists()
    if server_cwd_terminal_created:
        server_cwd_terminal_marker.unlink()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert requested_file.read_text(encoding="utf-8") == "request workspace file\n"
    assert (workspace / "terminal-marker.txt").read_text(encoding="utf-8") == "ok"
    assert server_cwd_created is False
    assert server_cwd_terminal_created is False
    assert len(provider_calls) == 2


def test_agent_loop_waits_for_approval_and_resumes_same_step(client, monkeypatch):
    _patch_respond(
        monkeypatch,
        [
            _response(tool_calls=[_tool_call("call_terminal", "terminal_run", {"argv": [sys.executable, "-c", "print('WAIT_OK')"]})]),
            _response(tool_calls=[_tool_call("call_followup", "terminal_run", {"argv": [sys.executable, "-c", "print('FOLLOWUP_OK')"]})]),
            _response(text="APPROVED_DONE"),
        ],
    )

    create_response = client.post(
        "/api/v1/taskRuns",
        json={
            "intent_type": "agent.loop",
            "owner_key": "approval-user",
            "input_payload": {
                "prompt": "승인 후 터미널 확인을 진행해줘.",
                "approval_required": True,
                "approval_reason": "터미널 실행 전 승인 필요",
            },
        },
    )

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["status"] == "WAITING"
    assert created["wait_payload"]["pending_tool_call_id"] == "call_terminal"
    assert created["wait_payload"]["pending_tool_name"] == "terminal.run"
    assert created["current_step_run_id"]

    events = client.get(f"/api/v1/taskRuns/{created['task_run_id']}/events").json()
    approval_id = next(event["payload"]["approval_id"] for event in events if event["event_type"] == "approval.requested")
    waiting_step_id = created["current_step_run_id"]

    resume_response = client.post(
        f"/api/v1/taskRuns/{created['task_run_id']}/resume",
        json={"approval_id": approval_id, "payload": {"approved": True}},
    )

    assert resume_response.status_code == 200
    resumed = resume_response.json()
    assert resumed["status"] == "COMPLETED"
    assert resumed["current_step_run_id"] == waiting_step_id
    assert resumed["result_payload"]["text"] == "APPROVED_DONE"
    assert [item["tool_call_id"] for item in resumed["result_payload"]["tool_results"]] == ["call_terminal", "call_followup"]

    resumed_events = client.get(f"/api/v1/taskRuns/{created['task_run_id']}/events").json()
    assert [event["event_type"] for event in resumed_events].count("approval.requested") == 1


def test_agent_loop_resume_provider_runtime_error_fails_existing_step(client, monkeypatch):
    _patch_respond(
        monkeypatch,
        [
            _response(tool_calls=[_tool_call("call_terminal", "terminal_run", {"argv": [sys.executable, "-c", "print('WAIT')"]})]),
            RuntimeError("provider unavailable"),
        ],
    )

    create_response = client.post(
        "/api/v1/taskRuns",
        json={
            "intent_type": "agent.loop",
            "owner_key": "resume-error-user",
            "input_payload": {
                "prompt": "승인 후 provider 오류를 실패로 저장해줘.",
                "approval_required": True,
            },
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["status"] == "WAITING"
    waiting_step_id = created["current_step_run_id"]

    events = client.get(f"/api/v1/taskRuns/{created['task_run_id']}/events").json()
    approval_id = next(event["payload"]["approval_id"] for event in events if event["event_type"] == "approval.requested")

    resume_response = client.post(
        f"/api/v1/taskRuns/{created['task_run_id']}/resume",
        json={"approval_id": approval_id, "payload": {"approved": True}},
    )

    assert resume_response.status_code == 200
    resumed = resume_response.json()
    assert resumed["status"] == "FAILED"
    assert resumed["current_step_run_id"] == waiting_step_id
    assert resumed["error_message"] == "RuntimeError: provider unavailable"

    steps = client.get(f"/api/v1/taskRuns/{created['task_run_id']}/steps").json()
    assert len(steps) == 1
    assert steps[0]["step_run_id"] == waiting_step_id
    assert steps[0]["status"] == "FAILED"
    assert steps[0]["error_message"] == "RuntimeError: provider unavailable"
    approval_detail = steps[0]["detail_json"]["approvalDetail"]
    assert approval_detail["approvalRequested"] is False
    assert approval_detail["approvalId"] == approval_id
    assert approval_detail["response"] == {"approved": True}


def test_taskruns_resume_rejects_missing_approval_id_for_waiting_task(client, monkeypatch):
    _patch_respond(
        monkeypatch,
        [
            _response(tool_calls=[_tool_call("call_terminal", "terminal_run", {"argv": [sys.executable, "-c", "print('WAIT')"]})]),
            _response(text="SHOULD_NOT_RESUME"),
        ],
    )

    create_response = client.post(
        "/api/v1/taskRuns",
        json={
            "intent_type": "agent.loop",
            "owner_key": "approval-missing-user",
            "input_payload": {"prompt": "승인 대기", "approval_required": True},
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["status"] == "WAITING"

    resume_response = client.post(
        f"/api/v1/taskRuns/{created['task_run_id']}/resume",
        json={"payload": {"approved": True}},
    )

    assert resume_response.status_code == 409
    assert "approval id is required" in resume_response.json()["detail"]
    assert client.get(f"/api/v1/taskRuns/{created['task_run_id']}").json()["status"] == "WAITING"


def test_taskruns_resume_rejects_approval_id_from_other_waiting_task(client, monkeypatch):
    _patch_respond(
        monkeypatch,
        [
            _response(tool_calls=[_tool_call("call_task_a", "terminal_run", {"argv": [sys.executable, "-c", "print('A')"]})]),
            _response(tool_calls=[_tool_call("call_task_b", "terminal_run", {"argv": [sys.executable, "-c", "print('B')"]})]),
            _response(text="SHOULD_NOT_RESUME"),
        ],
    )

    task_a_response = client.post(
        "/api/v1/taskRuns",
        json={
            "intent_type": "agent.loop",
            "owner_key": "approval-a",
            "input_payload": {"prompt": "A 작업", "approval_required": True},
        },
    )
    task_b_response = client.post(
        "/api/v1/taskRuns",
        json={
            "intent_type": "agent.loop",
            "owner_key": "approval-b",
            "input_payload": {"prompt": "B 작업", "approval_required": True},
        },
    )
    assert task_a_response.status_code == 200
    assert task_b_response.status_code == 200
    task_a = task_a_response.json()
    task_b = task_b_response.json()

    task_b_events = client.get(f"/api/v1/taskRuns/{task_b['task_run_id']}/events").json()
    task_b_approval_id = next(event["payload"]["approval_id"] for event in task_b_events if event["event_type"] == "approval.requested")

    resume_response = client.post(
        f"/api/v1/taskRuns/{task_a['task_run_id']}/resume",
        json={"approval_id": task_b_approval_id, "payload": {"approved": True}},
    )

    assert resume_response.status_code == 409
    assert "does not match open approval" in resume_response.json()["detail"]
    assert client.get(f"/api/v1/taskRuns/{task_a['task_run_id']}").json()["status"] == "WAITING"


def test_taskruns_cancel_records_pending_tool_result_without_resuming_loop(client, monkeypatch):
    provider_calls = _patch_respond(
        monkeypatch,
        [
            _response(tool_calls=[_tool_call("call_cancel", "terminal_run", {"argv": [sys.executable, "-c", "print('CANCEL')"]})]),
        ],
    )

    create_response = client.post(
        "/api/v1/taskRuns",
        json={
            "intent_type": "agent.loop",
            "owner_key": "cancel-user",
            "session_key": "sess_cancel_pending",
            "input_payload": {
                "prompt": "취소될 도구 실행",
                "approval_required": True,
                "approval_reason": "터미널 실행 전 승인 필요",
            },
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["status"] == "WAITING"

    cancel_response = client.post(f"/api/v1/taskRuns/{created['task_run_id']}/cancel")

    assert cancel_response.status_code == 200
    canceled = cancel_response.json()
    assert canceled["status"] == "CANCELED"
    assert len(provider_calls) == 1

    steps = client.get(f"/api/v1/taskRuns/{created['task_run_id']}/steps").json()
    step = next(item for item in steps if item["step_run_id"] == created["current_step_run_id"])
    tool_results = step["output_payload"]["tool_results"]
    assert tool_results[0]["tool_call_id"] == "call_cancel"
    assert tool_results[0]["name"] == "terminal.run"
    assert tool_results[0]["result"]["ok"] is False
    assert tool_results[0]["result"]["error"]["code"] == "tool_canceled"

    transcript_session = client.app.state.session_store.get_latest_session_by_key("sess_cancel_pending")
    transcript = client.app.state.session_store.list_messages(transcript_session["id"])
    tool_messages = [message for message in transcript if message["role"] == "tool"]
    assert len(tool_messages) == 1
    assert tool_messages[0]["tool_call_id"] == "call_cancel"
    assert tool_messages[0]["tool_name"] == "terminal.run"


def test_taskruns_resume_and_cancel_reject_non_waiting_task(client):
    create_response = client.post(
        "/api/v1/taskRuns",
        json={
            "intent_type": "agent.loop",
            "owner_key": "non-waiting-user",
            "input_payload": {"prompt": "바로 완료되는 작업"},
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["status"] == "COMPLETED"

    resume_response = client.post(f"/api/v1/taskRuns/{created['task_run_id']}/resume", json={"payload": {"approved": True}})
    assert resume_response.status_code == 409
    assert resume_response.json()["detail"] == "task is not waiting"

    cancel_response = client.post(f"/api/v1/taskRuns/{created['task_run_id']}/cancel")
    assert cancel_response.status_code == 409
    assert cancel_response.json()["detail"] == "task is not waiting"


def test_removed_legacy_routing_is_rejected(client):
    legacy_response = client.post(
        "/api/v1/taskRuns",
        json={
            "intent_type": "model.generate",
            "owner_key": "legacy-user",
            "input_payload": {"prompt": "legacy"},
        },
    )
    assert legacy_response.status_code == 400
    assert "legacy intent routing has been removed" in legacy_response.json()["detail"]

    workflow_response = client.post(
        "/api/v1/taskRuns",
        json={
            "intent_type": "agent.loop",
            "owner_key": "workflow-user",
            "input_payload": {"prompt": "workflow", "workflow_key": "workspace_publish_to_notion"},
        },
    )
    assert workflow_response.status_code == 400
    assert "workflow_key routing has been removed" in workflow_response.json()["detail"]


def test_runtime_tool_error_is_model_observation_not_immediate_task_failure(client, monkeypatch):
    _patch_respond(
        monkeypatch,
        [
            _response(tool_calls=[_tool_call("call_terminal", "terminal.run", {"argv": [sys.executable, "-c", "print('BLOCKED')"]})]),
            _response(text="BLOCKED_TOOL_REPORTED"),
        ],
    )

    response = client.post(
        "/api/v1/taskRuns",
        json={
            "intent_type": "agent.loop",
            "owner_key": "restricted-tools-user",
            "input_payload": {
                "prompt": "terminal tool should be reported as unavailable here.",
                "enabled_toolsets": ["skills"],
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    tool_result = body["result_payload"]["tool_results"][0]["result"]
    assert tool_result["ok"] is False
    assert tool_result["error"]["code"] == "tool_unavailable"


def test_taskruns_active_supports_session_filter_and_recent_terminal(client, monkeypatch):
    _patch_respond(
        monkeypatch,
        [
            _response(text="DONE"),
            _response(tool_calls=[_tool_call("call_terminal", "terminal.run", {"argv": [sys.executable, "-c", "print('WAIT')"]})]),
            _response(tool_calls=[_tool_call("call_terminal", "terminal.run", {"argv": [sys.executable, "-c", "print('WAIT')"]})]),
        ],
    )

    completed_response = client.post(
        "/api/v1/taskRuns",
        json={"intent_type": "agent.loop", "owner_key": "completed-user", "input_payload": {"prompt": "완료 작업"}},
    )
    assert completed_response.status_code == 200
    completed_task = completed_response.json()

    waiting_response = client.post(
        "/api/v1/taskRuns",
        json={
            "intent_type": "agent.loop",
            "owner_key": "waiting-user",
            "session_key": "sess_a",
            "input_payload": {"prompt": "대기 작업", "approval_required": True},
        },
    )
    assert waiting_response.status_code == 200
    waiting_task = waiting_response.json()
    assert waiting_task["status"] == "WAITING"

    active_response = client.get("/api/v1/taskRuns/active", params={"sessionKey": "sess_a"})
    assert active_response.status_code == 200
    active_body = active_response.json()
    assert active_body["total_count"] == 1
    assert active_body["items"][0]["task_run_id"] == waiting_task["task_run_id"]
    assert active_body["items"][0]["pendingApproval"]["approval_id"]
    assert active_body["items"][0]["pendingApproval"]["step_run_id"] == waiting_task["current_step_run_id"]
    assert active_body["items"][0]["pendingApproval"]["status"] == "PENDING"
    assert active_body["items"][0]["pendingApproval"]["reason"]
    assert active_body["items"][0]["pendingApproval"]["tool_call_id"] == "call_terminal"
    assert active_body["items"][0]["pendingApproval"]["tool_name"] == "terminal.run"
    assert active_body["items"][0]["pendingApproval"]["requested_at"]
    assert active_body["items"][0]["pendingApproval"]["can_approve"] is True
    assert active_body["items"][0]["pendingApproval"]["can_reject"] is True

    completed_at = datetime.fromisoformat(completed_task["updated_at"])
    monkeypatch.setattr("app.api.http.tasks.utc_now", lambda: completed_at + timedelta(seconds=301))
    expired_active = client.get("/api/v1/taskRuns/active", params={"sessionKey": "missing"})
    assert expired_active.status_code == 200
    assert expired_active.json()["items"] == []


def test_taskruns_flow_returns_observed_step_node(client, monkeypatch):
    _patch_respond(monkeypatch, [_response(text="FLOW_OK")])

    create_response = client.post(
        "/api/v1/taskRuns",
        json={
            "intent_type": "agent.loop",
            "owner_key": "flow-user",
            "input_payload": {"prompt": "흐름 확인", "model": "gpt-test"},
        },
    )

    assert create_response.status_code == 200
    created = create_response.json()
    flow_response = client.get(f"/api/v1/taskRuns/{created['task_run_id']}/flow")
    assert flow_response.status_code == 200
    flow = flow_response.json()
    assert flow["entry_executor_key"] == "agent.loop"
    assert len(flow["nodes"]) == 1
    assert flow["nodes"][0]["semantic"]["key"] == "agent.loop"
    assert flow["nodes"][0]["is_current"] is True
