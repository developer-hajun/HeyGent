from datetime import datetime, timedelta
import json
import sys

from app.contracts.provider.provider_response import ProviderGenerateResponse


def test_model_generate_tool_calls_and_skill_prompt(client):
    response = client.post(
        "/api/v1/taskRuns",
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
    assert "tool_results" in body["result_payload"]
    assert len(body["result_payload"]["tool_results"]) == 6

    steps_response = client.get(f"/api/v1/taskRuns/{body['task_run_id']}/steps")
    step = steps_response.json()[0]
    assert "skills.list" in step["detail_json"]["toolDetail"]["toolNames"]
    assert "terminal.run" in step["detail_json"]["toolDetail"]["toolNames"]
    assert step["detail_json"]["orchestration"]["entryExecutorKey"] == "model.generate"
    assert step["detail_json"]["semanticDetail"]["status"] == "completed"
    assert "Writing Plans" in step["output_payload"]["prompt"]
    assert "복잡한 구현을 시작하기 전에 목표" in step["output_payload"]["prompt"]


def test_model_generate_waits_for_approval_and_resumes(client):
    create_response = client.post(
        "/api/v1/taskRuns",
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
    waiting_steps = client.get(f"/api/v1/taskRuns/{created['task_run_id']}/steps").json()
    waiting_anchor_steps = [step for step in waiting_steps if not step["input_payload"].get("todo_key")]
    assert len(waiting_anchor_steps) == 1
    waiting_step_run_id = waiting_anchor_steps[0]["step_run_id"]
    assert waiting_anchor_steps[0]["status"] == "WAITING"

    events = client.get(f"/api/v1/taskRuns/{created['task_run_id']}/events").json()
    approval_event = [event for event in events if event["event_type"] == "approval.requested"]
    assert approval_event
    approval_id = approval_event[0]["payload"]["approval_id"]

    resume_response = client.post(
        f"/api/v1/taskRuns/{created['task_run_id']}/resume",
        json={"approval_id": approval_id, "payload": {"approved": True}},
    )
    resumed = resume_response.json()
    assert resume_response.status_code == 200
    assert resumed["status"] == "COMPLETED"
    resumed_steps = client.get(f"/api/v1/taskRuns/{created['task_run_id']}/steps").json()
    resumed_anchor_steps = [step for step in resumed_steps if not step["input_payload"].get("todo_key")]
    assert len(resumed_anchor_steps) == 1
    assert resumed_anchor_steps[0]["step_run_id"] == waiting_step_run_id
    assert resumed_anchor_steps[0]["status"] == "COMPLETED"

    flow_response = client.get(f"/api/v1/taskRuns/{created['task_run_id']}/flow")
    assert flow_response.status_code == 200
    flow = flow_response.json()
    anchor_nodes = [node for node in flow["nodes"] if not node["is_projected"]]
    assert len(anchor_nodes) == 1
    activity_types = [item["event_type"] for item in anchor_nodes[0]["activity"]]
    assert "approval.requested" in activity_types
    assert "approval.resolved" in activity_types


def test_taskruns_resume_rejects_non_waiting_task(client):
    create_response = client.post(
        "/api/v1/taskRuns",
        json={
            "intent_type": "model.generate",
            "owner_key": "non-waiting-user",
            "input_payload": {"prompt": "바로 완료되는 작업"},
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["status"] == "COMPLETED"

    resume_response = client.post(
        f"/api/v1/taskRuns/{created['task_run_id']}/resume",
        json={"payload": {"approved": True}},
    )
    assert resume_response.status_code == 409
    assert resume_response.json()["detail"] == "task is not waiting"

def test_model_generate_delegates_child_task(client):
    response = client.post(
        "/api/v1/taskRuns",
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

    child_task = client.get(f"/api/v1/taskRuns/{body['result_payload']['childTaskRunId']}").json()
    assert child_task["status"] == "COMPLETED"
    assert child_task["result_payload"]["text"]

    flow_response = client.get(f"/api/v1/taskRuns/{body['task_run_id']}/flow")
    assert flow_response.status_code == 200
    flow = flow_response.json()
    delegate_edges = [edge for edge in flow["edges"] if edge["relation"] == "delegates_to"]
    assert len(delegate_edges) == 1
    assert delegate_edges[0]["to_task_run_id"] == body["result_payload"]["childTaskRunId"]
    assert flow["nodes"][0]["child_task_run_id"] == body["result_payload"]["childTaskRunId"]
    assert flow["nodes"][0]["child_task"]["task_run_id"] == body["result_payload"]["childTaskRunId"]
    assert flow["nodes"][0]["child_task"]["status"] == "COMPLETED"
    assert flow["nodes"][0]["child_task"]["summary"]
    assert flow["nodes"][0]["child_task"]["agent_id"]


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
        "/api/v1/taskRuns",
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

    steps_response = client.get(f"/api/v1/taskRuns/{body['task_run_id']}/steps")
    steps = steps_response.json()
    anchor_steps = [step for step in steps if not step["input_payload"].get("todo_key")]
    assert len(anchor_steps) == 1
    step = anchor_steps[0]
    assert step["detail_json"]["llmDetail"]["callCount"] == 2
    assert step["detail_json"]["llmDetail"]["model"] == "gpt-5.4"
    assert step["detail_json"]["operationDetail"]["totalCount"] >= 2


def test_model_generate_keeps_repeated_tool_calls_as_distinct_operations(client, monkeypatch):
    response_payload = ProviderGenerateResponse(
        provider_name="openai_oauth",
        output_text='{"final":"REPEATED_TOOL_FINAL"}',
        usage={"output_tokens": 3},
        metadata={"mode": "stub", "model": "gpt-5.4"},
    )

    def fake_generate(self, prompt, **kwargs):
        return response_payload

    monkeypatch.setattr("app.domain.providers.model.openai_oauth.OpenAIOAuthProvider.generate", fake_generate)

    response = client.post(
        "/api/v1/taskRuns",
        json={
            "intent_type": "model.generate",
            "owner_key": "repeated-tool-user",
            "input_payload": {
                "prompt": "같은 tool 을 두 번 호출해도 step 안에서 둘 다 보여줘.",
                "tool_calls": [
                    {"name": "skills.list", "args": {}},
                    {"name": "skills.list", "args": {}},
                ],
                "model": "gpt-5.4",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"

    steps_response = client.get(f"/api/v1/taskRuns/{body['task_run_id']}/steps")
    step = steps_response.json()[0]
    operation_keys = [item["key"] for item in step["detail_json"]["operationDetail"]["operations"]]
    assert "tool.skills.list.1" in operation_keys
    assert "tool.skills.list.2" in operation_keys


def test_model_generate_executes_top_level_workflow_steps_from_workflow_key(client, monkeypatch):
    response_payload = ProviderGenerateResponse(
        provider_name="openai_oauth",
        output_text='{"final":"WORKFLOW_PLAN_OK"}',
        usage={"output_tokens": 3},
        metadata={"mode": "stub", "model": "gpt-5.4"},
    )

    def fake_generate(self, prompt, **kwargs):
        return response_payload

    monkeypatch.setattr("app.domain.providers.model.openai_oauth.OpenAIOAuthProvider.generate", fake_generate)

    response = client.post(
        "/api/v1/taskRuns",
        json={
            "intent_type": "model.generate",
            "owner_key": "workflow-plan-user",
            "input_payload": {
                "prompt": "작업 커밋부터 문서와 Notion 반영까지 진행 계획을 보여줘.",
                "workflow_key": "workspace_publish_to_notion",
                "model": "gpt-5.4",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["todo_state"]["currentKey"] is None
    assert [item["id"] for item in body["todo_state"]["items"]] == [
        "summarize_changes",
        "write_docs",
        "publish_notion_api_spec",
        "return_result",
    ]
    assert all(item["status"] == "completed" for item in body["todo_state"]["items"])

    steps = client.get(f"/api/v1/taskRuns/{body['task_run_id']}/steps").json()
    anchor_steps = [step for step in steps if not step["input_payload"].get("todo_key")]
    projected_steps = [step for step in steps if step["input_payload"].get("todo_key")]

    assert len(anchor_steps) == 1
    assert len(projected_steps) == 4
    assert anchor_steps[0]["title"] == "작업 커밋 분석 및 준비"
    assert anchor_steps[0]["detail_json"]["semanticDetail"]["semanticKey"] == (
        "workflow.workspace_publish_to_notion.analyze_commit"
    )
    assert [step["input_payload"]["todo_key"] for step in projected_steps] == [
        "summarize_changes",
        "write_docs",
        "publish_notion_api_spec",
        "return_result",
    ]
    assert projected_steps[-2]["executor_key"] == "notion.page.create"
    assert all(step["status"] == "COMPLETED" for step in projected_steps)


def test_model_generate_routes_handoff_to_explicit_step_executor(client, monkeypatch):
    response_payload = ProviderGenerateResponse(
        provider_name="openai_oauth",
        output_text='{"final":"HANDOFF_TO_NOTION"}',
        usage={"output_tokens": 3},
        metadata={"mode": "stub", "model": "gpt-5.4"},
    )

    def fake_generate(self, prompt, **kwargs):
        return response_payload

    monkeypatch.setattr("app.domain.providers.model.openai_oauth.OpenAIOAuthProvider.generate", fake_generate)

    response = client.post(
        "/api/v1/taskRuns",
        json={
            "intent_type": "model.generate",
            "owner_key": "workflow-routing-user",
            "input_payload": {
                "prompt": "먼저 내용을 정리하고 그 결과를 노션에 올려줘.",
                "task_plan": {
                    "title": "정리 후 노션 반영",
                    "steps": [
                        {
                            "key": "summarize",
                            "title": "변경 요약",
                            "goal": "변경 내용을 한 문단으로 요약한다.",
                            "entryExecutorKey": "model.generate",
                        },
                        {
                            "key": "publish_notion",
                            "title": "노션 페이지 반영",
                            "goal": "요약 결과를 노션 페이지로 남긴다.",
                            "entryExecutorKey": "notion.page.create",
                            "inputPayload": {"title": "API 변경 요약"},
                        },
                    ],
                },
                "model": "gpt-5.4",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["result_payload"]["notion"]["object"] == "page"
    assert body["todo_state"]["currentKey"] is None
    assert [item["status"] for item in body["todo_state"]["items"]] == ["completed"]

    steps = client.get(f"/api/v1/taskRuns/{body['task_run_id']}/steps").json()
    assert len(steps) == 2
    assert steps[0]["title"] == "변경 요약"
    assert steps[1]["title"] == "노션 페이지 반영"
    assert steps[1]["executor_key"] == "notion.page.create"
    assert steps[1]["output_payload"]["request"]["properties"]["title"] == "API 변경 요약"
    assert steps[0]["semantic"]["key"] == "plan.summarize"
    assert steps[0]["is_projected"] is False
    assert steps[1]["is_current"] is True


def test_model_generate_respects_runtime_toolsets(client):
    response = client.post(
        "/api/v1/taskRuns",
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
        "/api/v1/taskRuns",
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

    steps_response = client.get(f"/api/v1/taskRuns/{body['task_run_id']}/steps")
    steps = steps_response.json()
    assert len(steps) == 3
    projected_steps = [step for step in steps if step["input_payload"].get("todo_key")]
    assert [step["input_payload"]["todo_key"] for step in projected_steps] == ["plan", "ship"]
    assert projected_steps[0]["status"] == "COMPLETED"
    assert projected_steps[1]["status"] == "PENDING"
    assert projected_steps[0]["is_projected"] is True
    assert projected_steps[1]["is_projected"] is True


def test_taskruns_active_returns_only_live_task_snapshots(client):
    completed_response = client.post(
        "/api/v1/taskRuns",
        json={
            "intent_type": "model.generate",
            "owner_key": "completed-user",
            "input_payload": {"prompt": "완료된 작업 하나를 만든다."},
        },
    )
    assert completed_response.status_code == 200
    assert completed_response.json()["status"] == "COMPLETED"

    waiting_response = client.post(
        "/api/v1/taskRuns",
        json={
            "intent_type": "model.generate",
            "owner_key": "waiting-user",
            "input_payload": {
                "prompt": "승인 전까지 기다린다.",
                "approval_required": True,
                "approval_reason": "운영 반영 승인 필요",
            },
        },
    )
    assert waiting_response.status_code == 200
    waiting_task = waiting_response.json()
    assert waiting_task["status"] == "WAITING"

    active_response = client.get("/api/v1/taskRuns/active")
    assert active_response.status_code == 200
    body = active_response.json()

    assert body["total_count"] == 2
    assert len(body["items"]) == 2
    active_item = body["items"][0]
    assert active_item["task_run_id"] == waiting_task["task_run_id"]
    assert active_item["source"] == "active"
    assert active_item["status"] == "WAITING"
    assert active_item["wait_reason"] == "approval_required"
    assert active_item["current_step"]["status"] == "WAITING"
    assert active_item["current_step_run_id"] == waiting_task["current_step_run_id"]
    recent_item = body["items"][1]
    assert recent_item["source"] == "recent"
    assert recent_item["status"] == "COMPLETED"


def test_taskruns_active_excludes_recent_terminal_tasks_after_ttl(client, monkeypatch):
    completed_response = client.post(
        "/api/v1/taskRuns",
        json={
            "intent_type": "model.generate",
            "owner_key": "recent-expired-user",
            "input_payload": {"prompt": "곧 recent TTL 에서 사라질 작업"},
        },
    )
    assert completed_response.status_code == 200
    completed_task = completed_response.json()
    completed_at = datetime.fromisoformat(completed_task["updated_at"])

    monkeypatch.setattr(
        "app.api.http.tasks.utc_now",
        lambda: completed_at + timedelta(seconds=301),
    )

    active_response = client.get("/api/v1/taskRuns/active")
    assert active_response.status_code == 200
    body = active_response.json()
    assert body["total_count"] == 0
    assert body["items"] == []


def test_taskruns_flow_returns_step_nodes_and_edges_for_workflow(client, monkeypatch):
    response_payload = ProviderGenerateResponse(
        provider_name="openai_oauth",
        output_text='{"final":"FLOW_OK"}',
        usage={"output_tokens": 3},
        metadata={"mode": "stub", "model": "gpt-5.4"},
    )

    def fake_generate(self, prompt, **kwargs):
        return response_payload

    monkeypatch.setattr("app.domain.providers.model.openai_oauth.OpenAIOAuthProvider.generate", fake_generate)

    create_response = client.post(
        "/api/v1/taskRuns",
        json={
            "intent_type": "model.generate",
            "owner_key": "flow-user",
            "input_payload": {
                "prompt": "커밋 분석부터 노션 반영까지 순서를 보여줘.",
                "workflow_key": "workspace_publish_to_notion",
                "model": "gpt-5.4",
            },
        },
    )

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["status"] == "COMPLETED"

    flow_response = client.get(f"/api/v1/taskRuns/{created['task_run_id']}/flow")
    assert flow_response.status_code == 200
    flow = flow_response.json()

    assert flow["task_run_id"] == created["task_run_id"]
    assert flow["status"] == "COMPLETED"
    assert flow["entry_executor_key"] == "model.generate"
    assert flow["current_step_run_id"] == created["current_step_run_id"]
    assert len(flow["nodes"]) == 5
    assert len(flow["edges"]) == 4
    assert [edge["relation"] for edge in flow["edges"]] == ["next", "next", "next", "next"]
    assert flow["nodes"][0]["semantic"]["key"] == "workflow.workspace_publish_to_notion.analyze_commit"
    assert flow["nodes"][0]["is_projected"] is False
    assert [node["is_projected"] for node in flow["nodes"][1:]] == [True, True, True, True]
    assert flow["nodes"][3]["executor_key"] == "notion.page.create"
    assert sum(1 for node in flow["nodes"] if node["is_current"]) == 1
    assert flow["nodes"][-1]["step_run_id"] == flow["current_step_run_id"]
    assert any(item["event_type"] == "step.started" for item in flow["nodes"][0]["activity"])
    assert any(item["event_type"] == "task.completed" for item in flow["nodes"][-1]["activity"])

