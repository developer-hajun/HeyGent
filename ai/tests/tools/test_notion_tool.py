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


def test_notion_execute_handler_blocks_workspace_parent_page_creation(monkeypatch):
    def fail_client():
        raise AssertionError("workspace-level page creation must be blocked before backend call")

    monkeypatch.setattr(notion_tool, "BackendNotionClient", fail_client)

    result = notion_tool.execute_notion_handler(
        {
            "_trusted_user_id": "7",
            "commands": [
                {
                    "method": "POST",
                    "endpoint": "/v1/pages",
                    "params": {
                        "parent": {"workspace": True},
                        "properties": {"title": [{"text": {"content": "테스트용입니다"}}]},
                    },
                }
            ],
        }
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "workspace_parent_page_blocked"


def test_notion_execute_handler_blocks_post_block_children(monkeypatch):
    def fail_client():
        raise AssertionError("invalid block children POST must be blocked before backend call")

    monkeypatch.setattr(notion_tool, "BackendNotionClient", fail_client)

    result = notion_tool.execute_notion_handler(
        {
            "_trusted_user_id": "7",
            "commands": [
                {
                    "method": "POST",
                    "endpoint": "/v1/blocks/2ceba9bf-a561-80a0-b9a0-e5d7d2ef9a2b/children",
                    "params": {"page_size": 5},
                }
            ],
        }
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "invalid_block_children_method"


def test_notion_execute_handler_treats_already_archived_retry_as_success(monkeypatch):
    class AlreadyArchivedClient:
        def execute(self, *, user_id, commands):
            return [
                {
                    "index": 0,
                    "userId": user_id,
                    "method": commands[0]["method"],
                    "endpoint": commands[0]["endpoint"],
                    "notionVersion": commands[0]["notionVersion"],
                    "success": False,
                    "data": None,
                    "errorCode": "VALIDATION_ERROR",
                    "errorMessage": "Can't edit block that is archived. You must unarchive the block before editing.",
                }
            ]

    monkeypatch.setattr(notion_tool, "BackendNotionClient", lambda: AlreadyArchivedClient())

    result = notion_tool.execute_notion_handler(
        {
            "_trusted_user_id": "7",
            "commands": [
                {
                    "method": "PATCH",
                    "endpoint": "/v1/pages/360ba9bf-a561-8183-83a0-f087ee3db58a",
                    "params": {"in_trash": True},
                }
            ],
        }
    )

    assert result["ok"] is True
    assert result["failed_count"] == 0
    assert result["results"][0]["data"]["in_trash"] is True
