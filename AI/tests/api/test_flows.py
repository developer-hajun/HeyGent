def test_list_flows(client):
    response = client.get("/flows")

    assert response.status_code == 200
    assert "notion_page_create" in response.json()


def test_execute_notion_flow(client):
    response = client.post(
        "/flows/notion_page_create/execute",
        json={"input_payload": {"title": "Backlog", "content": "todo"}},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "COMPLETED"
    assert body["result_payload"]["notion"]["object"] == "page"
