from __future__ import annotations


def terminal_tool_definition() -> dict[str, str]:
    return {
        "toolset": "terminal",
        "module": "app.tools.terminal.terminal_tool",
        "summary": "Terminal execution tool slot.",
    }
