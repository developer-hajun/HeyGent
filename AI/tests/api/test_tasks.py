def test_create_echo_task_and_read_back(client):
    response = client.post("/api/v1/tasks", json={"flow_name": "echo_flow", "input_payload": {"message": "hello"}})
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "COMPLETED"
    assert data["result_payload"]["echo"] == {"message": "hello"}

    task_response = client.get(f"/api/v1/tasks/{data['task_run_id']}")
    steps_response = client.get(f"/api/v1/tasks/{data['task_run_id']}/steps")
    events_response = client.get(f"/api/v1/tasks/{data['task_run_id']}/events")

    assert task_response.status_code == 200
    assert steps_response.status_code == 200
    assert steps_response.json()[0]["status"] == "COMPLETED"
    assert any(event["event_type"] == "task.completed" for event in events_response.json())


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
    assert "task.completed" in event_types
