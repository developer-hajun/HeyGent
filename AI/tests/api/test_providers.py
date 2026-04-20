def test_list_providers(client):
    response = client.get("/providers")

    assert response.status_code == 200
    assert response.json()[0]["provider_name"] == "openai_oauth"


def test_provider_generate(client):
    response = client.post(
        "/providers/generate",
        json={"provider_name": "openai_oauth", "prompt": "summarize this", "metadata": {"temperature": 0}},
    )

    assert response.status_code == 200
    assert response.json()["output_text"].startswith("[stub:openai_oauth]")
