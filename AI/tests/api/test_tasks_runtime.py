from __future__ import annotations

from datetime import datetime, timedelta
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


def _patch_respond(monkeypatch, responses: list[AgentModelResponse]) -> list[dict]:
    iterator = iter(responses)
    calls: list[dict] = []

    def fake_respond(self, messages, tools, model, tool_choice=None):
        calls.append({"messages": messages, "tools": tools, "model": model, "tool_choice": tool_choice})
        return next(iterator)

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
    assert body["todo_state"]["currentKey"] == "ship"
    exposed_tool_names = [tool["function"]["name"] for tool in provider_calls[0]["tools"]]
    assert "skills_list" in exposed_tool_names
    assert "terminal_run" in exposed_tool_names
    assert all("." not in name for name in exposed_tool_names)

    steps = client.get(f"/api/v1/taskRuns/{body['task_run_id']}/steps").json()
    assert len([step for step in steps if not step["input_payload"].get("todo_key")]) == 1
    projected_steps = [step for step in steps if step["input_payload"].get("todo_key")]
    assert [step["input_payload"]["todo_key"] for step in projected_steps] == ["plan", "ship"]
    assert projected_steps[0]["status"] == "COMPLETED"
    assert projected_steps[1]["status"] == "PENDING"

    transcript_session = client.app.state.session_store.get_latest_session_by_key("sess_native_loop")
    transcript = client.app.state.session_store.list_messages(transcript_session["id"])
    assert [message["role"] for message in transcript] == ["user", "assistant", "tool", "tool", "tool", "assistant"]
    assert transcript[1]["tool_calls"][0]["id"] == "call_skills"
    assert transcript[2]["tool_call_id"] == "call_skills"


def test_agent_loop_waits_for_approval_and_resumes_same_step(client, monkeypatch):
    _patch_respond(
        monkeypatch,
        [
            _response(tool_calls=[_tool_call("call_terminal", "terminal_run", {"argv": [sys.executable, "-c", "print('WAIT_OK')"]})]),
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
    assert resumed["result_payload"]["tool_results"][0]["tool_call_id"] == "call_terminal"


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
