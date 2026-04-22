def test_health(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["api_prefix"] == "/api/v1"


def test_ready(client):
    response = client.get("/api/v1/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["db_path"].endswith("test.db")
    assert body["providers"][0]["provider_name"] == "openai_oauth"
