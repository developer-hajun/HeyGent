def test_create_echo_task_and_read_back(client):
    response = client.post("/api/v1/tasks", json={"flow_name": "echo_flow", "input_payload": {"message": "hello"}})
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
    assert steps_response.json()[0]["detail_json"]["agentDetail"]["called"] is False
    assert steps_response.json()[0]["detail_json"]["toolDetail"]["toolNames"] == []
    assert steps_response.json()[0]["detail_json"]["llmDetail"]["callCount"] == 0
    event_types = [event["event_type"] for event in events_response.json()]
    assert "step.created" in event_types
    assert "task.completed" in event_types


def test_approval_wait_and_resume(client):
    create_response = client.post("/api/v1/tasks", json={"flow_name": "approval_wait_flow", "input_payload": {"subject": "demo"}})
    task = create_response.json()

    assert create_response.status_code == 200
    assert task["status"] == "WAITING"
    assert task["wait_payload"]["reason"] == "approval_required"

    resume_response = client.post(
        f"/api/v1/tasks/{task['task_run_id']}/resume",
        json={"payload": {"approved": True, "comment": "go"}},
    )
    resumed = resume_response.json()
    events_response = client.get(f"/api/v1/tasks/{task['task_run_id']}/events")

    assert resume_response.status_code == 200
    assert resumed["status"] == "COMPLETED"
    assert resumed["result_payload"]["approved"] is True
    event_types = [event["event_type"] for event in events_response.json()]
    assert "approval.requested" in event_types
    assert "approval.resolved" in event_types
    assert "step.created" in event_types
    assert "task.completed" in event_types


def test_list_tasks_with_status_filter_and_current_step_summary(client):
    completed_task = client.post("/api/v1/tasks", json={"flow_name": "echo_flow", "input_payload": {"message": "first"}}).json()
    waiting_task = client.post("/api/v1/tasks", json={"flow_name": "approval_wait_flow", "input_payload": {"subject": "approval"}}).json()
    client.post("/api/v1/tasks", json={"flow_name": "echo_flow", "input_payload": {"message": "third"}}).json()

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
    assert payload["items"][0]["current_step"]["status"] == "WAITING"
    assert payload["items"][0]["current_step"]["title"] in {"승인 여부 확인", "사용자 승인 대기"}
    assert payload["items"][1]["status"] == "COMPLETED"
    assert payload["items"][1]["task_run_id"] != waiting_task["task_run_id"]

    assert waiting_response.status_code == 200
    waiting_payload = waiting_response.json()
    assert waiting_payload["status_filter"] == "WAITING"
    assert waiting_payload["total_count"] == 1
    assert waiting_payload["items"][0]["task_run_id"] == waiting_task["task_run_id"]
