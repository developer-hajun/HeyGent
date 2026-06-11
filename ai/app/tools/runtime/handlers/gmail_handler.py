"""Gmail tool 핸들러."""
from __future__ import annotations

from typing import Any

from app.tools.runtime.handlers.http_handler import _run_external_tool_handler


class GmailHandler:
    """gmail.execute tool 구현체."""

    def execute_gmail(self, args: dict[str, Any]) -> dict[str, Any]:
        return _run_external_tool_handler("app.tools.gmail.gmail_tool", "execute_gmail_handler", args)
