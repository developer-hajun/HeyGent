def test_list_providers(client):
    response = client.get("/api/v1/providers")

    assert response.status_code == 200
    assert response.json()[0]["provider_name"] == "openai_oauth"
    assert response.json()[0]["configured"] is False


def test_get_provider_detail(client):
    response = client.get("/api/v1/providers/openai_oauth")

    assert response.status_code == 200
    body = response.json()
    assert body["provider_name"] == "openai_oauth"
    assert "HEYGENT_OPENAI_OAUTH_CLIENT_ID" in body["missing_env"]


def test_provider_auth_start_returns_missing_env(client):
    response = client.post("/api/v1/providers/openai_oauth/auth", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "configuration_required"
    assert "HEYGENT_OPENAI_OAUTH_CLIENT_SECRET" in body["missing_env"]


def test_provider_generate(client):
    response = client.post(
        "/api/v1/providers/generate",
        json={"provider_name": "openai_oauth", "prompt": "summarize this", "metadata": {"temperature": 0}},
    )

    assert response.status_code == 200
    assert response.json()["output_text"].startswith("[stub:openai_oauth]")
