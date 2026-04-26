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


def _patch_respond(monkeypatch, responses: list[AgentModelResponse]) -> None:
    iterator = iter(responses)

    def fake_respond(self, messages, tools, model, tool_choice=None):
        return next(iterator)

    monkeypatch.setattr("app.domain.providers.model.openai_api.OpenAIAPIProvider.respond", fake_respond)
    monkeypatch.setattr("app.domain.providers.model.openai_oauth.OpenAIOAuthProvider.respond", fake_respond)


def test_agent_loop_executes_native_tool_calls_and_materializes_step(client, monkeypatch):
    _patch_respond(
        monkeypatch,
        [
            _response(
                tool_calls=[
                    _tool_call("call_skills", "skills.list", {}),
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
                    _tool_call("call_terminal", "terminal.run", {"argv": [sys.executable, "-c", "print('TOOL_OK')"]}),
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
            _response(tool_calls=[_tool_call("call_terminal", "terminal.run", {"argv": [sys.executable, "-c", "print('WAIT_OK')"]})]),
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
