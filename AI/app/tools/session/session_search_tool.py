from __future__ import annotations


def session_search_tool_definition() -> dict[str, str]:
    return {
        "toolset": "session",
        "module": "app.tools.session.session_search_tool",
        "summary": "Session recall/search tool slot.",
    }
