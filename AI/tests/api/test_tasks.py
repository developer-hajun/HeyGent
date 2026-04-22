def test_create_echo_task_and_read_back(client):
    response = client.post("/api/v1/tasks", json={"intent_type": "stub.echo", "input_payload": {"message": "hello"}})
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "COMPLETED"
    assert data["title"] == "Echo 응답 태스크"
    assert data["result_payload"]["echo"] == {"message": "hello"}

    task_response = client.get(f"/api/v1/tasks/{data['task_run_id']}")
    steps_response = client.get(f"/api/v1/tasks/{data['task_run_id']}/steps")
    events_response = client.get(f"/api/v1/tasks/{data['task_run_id']}/events")

    assert task_response.status_code == 200
    assert steps_response.status_code == 200
    assert steps_response.json()[0]["status"] == "COMPLETED"
    assert steps_response.json()[0]["title"] == "입력 메시지 반영"
    assert steps_response.json()[0]["detail_json"]["semanticDetail"]["semanticKey"] == "echo.reply"
    assert steps_response.json()[0]["detail_json"]["semanticDetail"]["lifecycle"] == "completed"
    assert steps_response.json()[0]["detail_json"]["operationDetail"]["completedCount"] == 1
    assert steps_response.json()[0]["detail_json"]["planningDetail"]["completedCount"] == 1
    assert steps_response.json()[0]["detail_json"]["agentDetail"]["called"] is False
    assert steps_response.json()[0]["detail_json"]["toolDetail"]["toolNames"] == []
    assert steps_response.json()[0]["detail_json"]["llmDetail"]["callCount"] == 0
    event_types = [event["event_type"] for event in events_response.json()]
    assert "step.created" in event_types
    assert "task.completed" in event_types


def test_approval_wait_and_resume(client):
    create_response = client.post("/api/v1/tasks", json={"intent_type": "stub.approval_wait", "input_payload": {"subject": "demo"}})
    task = create_response.json()
    waiting_steps = client.get(f"/api/v1/tasks/{task['task_run_id']}/steps").json()
    waiting_step_id = waiting_steps[0]["step_run_id"]

    assert create_response.status_code == 200
    assert task["status"] == "WAITING"
    assert task["wait_payload"]["reason"] == "approval_required"
    assert task["wait_payload"]["approval_id"]
    assert waiting_steps[0]["detail_json"]["approvalDetail"]["approvalRequested"] is True
    assert waiting_steps[0]["detail_json"]["approvalDetail"]["approvalId"] == task["wait_payload"]["approval_id"]
    assert waiting_steps[0]["detail_json"]["semanticDetail"]["lifecycle"] == "waiting"
    assert waiting_steps[0]["detail_json"]["operationDetail"]["completedCount"] == 1

    resume_response = client.post(
        f"/api/v1/tasks/{task['task_run_id']}/resume",
        json={"payload": {"approved": True, "comment": "go"}},
    )
    resumed = resume_response.json()
    events_response = client.get(f"/api/v1/tasks/{task['task_run_id']}/events")
    resumed_steps = client.get(f"/api/v1/tasks/{task['task_run_id']}/steps").json()

    assert resume_response.status_code == 200
    assert resumed["status"] == "COMPLETED"
    assert resumed["result_payload"]["approved"] is True
    assert resumed_steps[0]["step_run_id"] == waiting_step_id
    assert resumed_steps[0]["detail_json"]["approvalDetail"]["response"] == {"approved": True, "comment": "go"}
    assert resumed_steps[0]["detail_json"]["semanticDetail"]["lifecycle"] == "completed"
    assert resumed_steps[0]["detail_json"]["operationDetail"]["completedCount"] == 2
    event_types = [event["event_type"] for event in events_response.json()]
    assert "approval.requested" in event_types
    assert "approval.resolved" in event_types
    assert "step.created" in event_types
    assert "task.completed" in event_types


def test_list_tasks_with_status_filter_and_current_step_summary(client):
    completed_task = client.post("/api/v1/tasks", json={"intent_type": "stub.echo", "input_payload": {"message": "first"}}).json()
    waiting_task = client.post("/api/v1/tasks", json={"intent_type": "stub.approval_wait", "input_payload": {"subject": "approval"}}).json()
    client.post("/api/v1/tasks", json={"intent_type": "stub.echo", "input_payload": {"message": "third"}}).json()

    list_response = client.get("/api/v1/tasks?page=1&page_size=2&status=ALL")
    waiting_response = client.get("/api/v1/tasks?page=1&page_size=5&status=WAITING")

    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["page"] == 1
    assert payload["page_size"] == 2
    assert payload["total_count"] == 3
    assert payload["has_next"] is True
    assert len(payload["items"]) == 2
    assert payload["items"][0]["task_run_id"] == waiting_task["task_run_id"]
    assert payload["items"][0]["title"] == "승인 대기 태스크"
    assert payload["items"][0]["input_summary"] == "approval"
    assert payload["items"][0]["step_count"] == 1
    assert payload["items"][0]["current_step"]["status"] == "WAITING"
    assert payload["items"][0]["current_step"]["title"] in {"승인 여부 확인", "사용자 승인 대기"}
    assert payload["items"][1]["status"] == "COMPLETED"
    assert payload["items"][1]["input_summary"] in {"first", "third"}
    assert payload["items"][1]["task_run_id"] != waiting_task["task_run_id"]

    assert waiting_response.status_code == 200
    waiting_payload = waiting_response.json()
    assert waiting_payload["status_filter"] == "WAITING"
    assert waiting_payload["total_count"] == 1
    assert waiting_payload["items"][0]["task_run_id"] == waiting_task["task_run_id"]


def test_delegate_child_task_linkage(client):
    create_response = client.post("/api/v1/tasks", json={"intent_type": "stub.delegate_echo", "input_payload": {"message": "child hello"}})
    task = create_response.json()
    steps = client.get(f"/api/v1/tasks/{task['task_run_id']}/steps").json()
    listed = client.get("/api/v1/tasks?page=1&page_size=10&status=ALL").json()

    assert create_response.status_code == 200
    assert task["status"] == "COMPLETED"
    assert task["result_payload"]["delegated"] is True
    assert task["result_payload"]["childTaskRunId"]
    assert steps[0]["detail_json"]["agentDetail"]["called"] is True
    assert steps[0]["detail_json"]["agentDetail"]["childTaskRunId"] == task["result_payload"]["childTaskRunId"]
    assert steps[0]["detail_json"]["agentDetail"]["status"] == "COMPLETED"
    assert steps[0]["output_payload"]["childStatus"] == "COMPLETED"
    assert steps[0]["detail_json"]["operationDetail"]["completedCount"] == 2
    assert len(listed["items"]) == 2
    child_ids = {item["task_run_id"] for item in listed["items"]}
    assert task["result_payload"]["childTaskRunId"] in child_ids
