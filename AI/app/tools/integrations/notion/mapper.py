from __future__ import annotations

from typing import Any


class NotionMapper:
    """HeyGent 입력을 Notion 요청 형태로 바꾸는 전용 매퍼다."""

    def to_page_create(self, payload: dict[str, Any]) -> dict[str, Any]:
        title = payload.get("title", "Untitled")
        content = payload.get("content", "")
        parent_id = payload.get("parent_page_id", "local-parent")
        return {
            "parent": {"page_id": parent_id},
            "properties": {"title": title},
            "children": [{"type": "paragraph", "text": content}],
        }

    def to_database_append(self, payload: dict[str, Any]) -> dict[str, Any]:
        database_id = payload.get("database_id", "local-database")
        fields = payload.get("fields", {})
        return {
            "parent": {"database_id": database_id},
            "properties": fields,
        }

    def summarize_result(self, result: dict[str, Any]) -> dict[str, Any]:
        return {
            "resource_id": result.get("id", "stub-resource"),
            "url": result.get("url", "https://notion.local/stub"),
            "object": result.get("object", "page"),
        }
