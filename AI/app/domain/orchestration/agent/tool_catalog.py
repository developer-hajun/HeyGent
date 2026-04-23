from __future__ import annotations

from app.tools.runtime import resolve_runtime_tool_names


class ToolCatalog:
    """Expose runtime tools available to the local agent loop."""

    def __init__(self, tool_runtime, *, default_toolsets: tuple[str, ...] | None = None) -> None:
        self.tool_runtime = tool_runtime
        self.default_toolsets = default_toolsets

    def list_available_tools(self, *, requested_toolsets: tuple[str, ...] | None = None) -> list[dict[str, str]]:
        active_toolsets = requested_toolsets or self.default_toolsets
        if resolve_runtime_tool_names(active_toolsets) is None:
            return self.tool_runtime.list_tool_definitions()
        return self.tool_runtime.list_tool_definitions(enabled_toolsets=tuple(active_toolsets or ()))

    def list_enabled_tools(self, *, requested_toolsets: tuple[str, ...] | None = None) -> list[str]:
        return [str(tool["name"]) for tool in self.list_available_tools(requested_toolsets=requested_toolsets)]
