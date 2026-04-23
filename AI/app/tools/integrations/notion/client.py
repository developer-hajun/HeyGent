from __future__ import annotations

from typing import Any


class NotionClient:
    """실제 외부 호출 대신 안전한 스텁 응답을 반환하는 Notion 클라이언트다."""

    def __init__(self, api_base_url: str) -> None:
        self.api_base_url = api_base_url.rstrip("/")

    def create_page(self, payload: dict[str, Any]) -> dict[str, Any]:
        title = payload.get("properties", {}).get("title", "Untitled")
        return {
            "id": f"page-{title}".replace(" ", "-").lower(),
            "url": f"{self.api_base_url}/pages/stub",
            "object": "page",
            "request": payload,
        }

    def append_database_item(self, payload: dict[str, Any]) -> dict[str, Any]:
        database_id = payload.get("parent", {}).get("database_id", "local-database")
        return {
            "id": f"db-item-{database_id}",
            "url": f"{self.api_base_url}/databases/{database_id}/stub",
            "object": "page",
            "request": payload,
        }
