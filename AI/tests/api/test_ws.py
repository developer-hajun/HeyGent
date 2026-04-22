def test_websocket_receives_task_events(client):
    with client.websocket_connect("/api/v1/gateway/ws") as websocket:
        websocket.send_json({"action": "subscribe", "task_run_id": "all"})
        ack = websocket.receive_json()

        assert ack["type"] == "subscribed"
        websocket.send_json({"action": "ping"})
        ping_pong = websocket.receive_json()
        assert ping_pong["type"] == "pong"

        client.post("/api/v1/tasks", json={"intent_type": "stub.echo", "input_payload": {"message": "event"}})
        event = websocket.receive_json()
        assert event["type"] == "task.event"
        assert event["data"]["event_type"].startswith("task.")
