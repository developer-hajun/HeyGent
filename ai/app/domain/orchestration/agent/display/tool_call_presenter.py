from __future__ import annotations


class ToolCallPresenter:
    def present(self, operation: dict) -> str:
        key = str(operation.get("key") or "tool")
        status = str(operation.get("status") or "unknown")
        return f"{key} ({status})"
