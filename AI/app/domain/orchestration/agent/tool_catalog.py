from __future__ import annotations


class ToolCatalog:
    """Expose enabled executor keys for the current runtime session."""

    def __init__(self, tool_registry) -> None:
        self.tool_registry = tool_registry

    def list_enabled_tools(self) -> list[str]:
        return self.tool_registry.list_executor_keys()
