import json
import sys

from app.contracts.provider.provider_response import ProviderGenerateResponse


def test_model_generate_tool_calls_and_skill_prompt(client):
    response = client.post(
        "/api/v1/tasks",
        json={
            "intent_type": "model.generate",
            "entry_executor_key": "model.generate",
            "owner_key": "tool-user",
            "input_payload": {
                "prompt": "도구 결과와 스킬 힌트를 짧게 요약해줘.",
                "skill_hints": ["writing-plans"],
                "tool_calls": [
                    {"name": "skills.list", "args": {}},
                    {"name": "skills.read", "args": {"skill_name": "writing-plans"}},
                    {"name": "session.record", "args": {"session_key": "runtime-test", "content": "alpha memo"}},
                    {"name": "session.search", "args": {"query": "alpha", "limit": 3}},
                    {"name": "todo.write", "args": {"todos": [{"key": "t1", "title": "정리", "status": "pending"}]}},
                    {"name": "terminal.run", "args": {"argv": [sys.executable, "-c", "print('TOOL_OK')"]}},
                ],
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["entry_executor_key"] == "model.generate"
    assert "entry_capability" not in body
    assert "tool_results" in body["result_payload"]
    assert len(body["result_payload"]["tool_results"]) == 6

    steps_response = client.get(f"/api/v1/tasks/{body['task_run_id']}/steps")
    step = steps_response.json()[0]
    assert "skills.list" in step["detail_json"]["toolDetail"]["toolNames"]
    assert "terminal.run" in step["detail_json"]["toolDetail"]["toolNames"]
    assert step["detail_json"]["orchestration"]["entryExecutorKey"] == "model.generate"
    assert "entryCapability" not in step["detail_json"]["orchestration"]
    assert step["detail_json"]["semanticDetail"]["status"] == "completed"
    assert "Writing Plans" in step["output_payload"]["prompt"]
    assert "복잡한 구현을 시작하기 전에 목표" in step["output_payload"]["prompt"]


def test_model_generate_waits_for_approval_and_resumes(client):
    create_response = client.post(
        "/api/v1/tasks",
        json={
            "intent_type": "model.generate",
            "owner_key": "approval-user",
            "input_payload": {
                "prompt": "승인 이후 처리 결과를 한 줄로 알려줘.",
                "approval_required": True,
                "approval_reason": "운영 반영 전에 확인 필요",
            },
        },
    )

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["status"] == "WAITING"
    assert created["wait_payload"]["reason"] == "approval_required"

    events = client.get(f"/api/v1/tasks/{created['task_run_id']}/events").json()
    approval_event = [event for event in events if event["event_type"] == "approval.requested"]
    assert approval_event
    approval_id = approval_event[0]["payload"]["approval_id"]

    resume_response = client.post(
        f"/api/v1/tasks/{created['task_run_id']}/resume",
        json={"approval_id": approval_id, "payload": {"approved": True}},
    )
    resumed = resume_response.json()
    assert resume_response.status_code == 200
    assert resumed["status"] == "COMPLETED"


def test_create_task_accepts_legacy_entry_capability(client):
    response = client.post(
        "/api/v1/tasks",
        json={
            "intent_type": "model.generate",
            "entry_capability": "model.generate",
            "owner_key": "legacy-user",
            "input_payload": {"prompt": "legacy entry capability input"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["entry_executor_key"] == "model.generate"
    assert "entry_capability" not in body


def test_model_generate_delegates_child_task(client):
    response = client.post(
        "/api/v1/tasks",
        json={
            "intent_type": "model.generate",
            "owner_key": "delegate-user",
            "input_payload": {
                "prompt": "부모 작업이 자식 작업을 위임했다는 사실만 짧게 요약해줘.",
                "delegate_prompt": "Reply with exactly CHILD_DELEGATE_OK and nothing else.",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["result_payload"]["delegation_requested"] is True
    assert body["result_payload"]["childTaskRunId"].startswith("task_")

    child_task = client.get(f"/api/v1/tasks/{body['result_payload']['childTaskRunId']}").json()
    assert child_task["status"] == "COMPLETED"
    assert child_task["result_payload"]["text"]


def test_model_generate_executes_model_requested_tool_loop(client, monkeypatch):
    responses = iter(
        [
            ProviderGenerateResponse(
                provider_name="openai_oauth",
                output_text=json.dumps(
                    {
                        "tool_calls": [
                            {"name": "skills.list", "args": {}},
                            {"name": "terminal.run", "args": {"argv": [sys.executable, "-c", "print('MODEL_LOOP_OK')"]}},
                        ]
                    },
                    ensure_ascii=False,
                )
                + "\nRunning the required tools first.",
                usage={},
                metadata={"mode": "stub", "model": "gpt-5.4"},
            ),
            ProviderGenerateResponse(
                provider_name="openai_oauth",
                output_text='{"final":"MODEL_LOOP_FINAL"}',
                usage={"output_tokens": 5},
                metadata={"mode": "stub", "model": "gpt-5.4"},
            ),
        ]
    )

    def fake_generate(self, prompt, **kwargs):
        return next(responses)

    monkeypatch.setattr("app.domain.providers.model.openai_oauth.OpenAIOAuthProvider.generate", fake_generate)

    response = client.post(
        "/api/v1/tasks",
        json={
            "intent_type": "model.generate",
            "owner_key": "loop-user",
            "input_payload": {
                "prompt": "필요하면 도구를 쓰고 마지막에 MODEL_LOOP_FINAL 이라고 답해.",
                "model": "gpt-5.4",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["result_payload"]["text"] == "MODEL_LOOP_FINAL"
    assert [item["name"] for item in body["result_payload"]["tool_results"]] == ["skills.list", "terminal.run"]

    steps_response = client.get(f"/api/v1/tasks/{body['task_run_id']}/steps")
    step = steps_response.json()[0]
    assert step["detail_json"]["llmDetail"]["callCount"] == 2
    assert step["detail_json"]["llmDetail"]["model"] == "gpt-5.4"


def test_model_generate_respects_runtime_toolsets(client):
    response = client.post(
        "/api/v1/tasks",
        json={
            "intent_type": "model.generate",
            "owner_key": "restricted-tools-user",
            "input_payload": {
                "prompt": "terminal tool should be blocked here.",
                "enabled_toolsets": ["skills"],
                "tool_calls": [
                    {"name": "terminal.run", "args": {"argv": [sys.executable, "-c", "print('BLOCKED')"]}},
                ],
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "FAILED"
    assert "unknown or disabled runtime tool: terminal.run" in body["error_message"]


def test_model_generate_promotes_todo_state_and_materializes_todo_steps(client):
    response = client.post(
        "/api/v1/tasks",
        json={
            "intent_type": "model.generate",
            "owner_key": "todo-user",
            "input_payload": {
                "prompt": "todo 상태를 기록하고 끝내.",
                "tool_calls": [
                    {
                        "name": "todo.write",
                        "args": {
                            "todos": [
                                {"id": "plan", "content": "계획 정리", "status": "completed"},
                                {"id": "ship", "content": "배포 점검", "status": "pending"},
                            ]
                        },
                    }
                ],
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["todo_state"]["currentKey"] == "ship"
    assert [item["id"] for item in body["todo_state"]["items"]] == ["plan", "ship"]

    steps_response = client.get(f"/api/v1/tasks/{body['task_run_id']}/steps")
    steps = steps_response.json()
    assert len(steps) == 3
    projected_steps = [step for step in steps if step["input_payload"].get("todo_key")]
    assert [step["input_payload"]["todo_key"] for step in projected_steps] == ["plan", "ship"]
    assert projected_steps[0]["status"] == "COMPLETED"
    assert projected_steps[1]["status"] == "PENDING"
