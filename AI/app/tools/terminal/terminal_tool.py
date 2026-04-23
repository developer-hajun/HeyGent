from __future__ import annotations

from app.tools.runtime.catalog import register_runtime_tool_definition


_TERMINAL_TOOL_DEFINITION = register_runtime_tool_definition(
    name="terminal.run",
    toolset="terminal",
    module="app.tools.terminal.terminal_tool",
    summary="Terminal execution tool slot.",
)

def terminal_tool_definition() -> dict[str, str]:
    return {
        "name": _TERMINAL_TOOL_DEFINITION.name,
        "toolset": _TERMINAL_TOOL_DEFINITION.toolset,
        "module": _TERMINAL_TOOL_DEFINITION.module,
        "summary": _TERMINAL_TOOL_DEFINITION.summary,
    }
