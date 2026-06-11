"""Notion tool 핸들러.

notion.execute 도구의 구현체.
"""
from __future__ import annotations

from typing import Any

from app.tools.runtime.handlers.http_handler import _run_external_tool_handler


class NotionHandler:
    """notion.execute tool 구현체."""

    def execute_notion(self, args: dict[str, Any]) -> dict[str, Any]:
        return _run_external_tool_handler("app.tools.notion.notion_tool", "execute_notion_handler", args)
