from app.tools.notion import notion_tool


class FakeBackendNotionClient:
    def execute(self, *, user_id, commands):
        return [
            {
                "index": 0,
                "userId": user_id,
                "method": commands[0]["method"],
                "endpoint": commands[0]["endpoint"],
                "notionVersion": commands[0]["notionVersion"],
                "success": True,
                "data": {"object": "list"},
            }
        ]


def test_notion_execute_handler_uses_trusted_user_and_default_version(monkeypatch):
    monkeypatch.setattr(notion_tool, "BackendNotionClient", lambda: FakeBackendNotionClient())

    result = notion_tool.execute_notion_handler(
        {
            "_trusted_user_id": "7",
            "userId": 999,
            "commands": [
                {
                    "method": "post",
                    "endpoint": "/v1/search",
                    "params": {"query": "테스트용입니다"},
                }
            ],
        }
    )

    assert result["ok"] is True
    first = result["results"][0]
    assert first["userId"] == 7
    assert first["method"] == "POST"
    assert first["endpoint"] == "/v1/search"
    assert first["notionVersion"] == "2026-03-11"


def test_notion_execute_handler_requires_trusted_user():
    result = notion_tool.execute_notion_handler(
        {
            "commands": [
                {
                    "method": "POST",
                    "endpoint": "/v1/search",
                }
            ],
        }
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "missing_user"
