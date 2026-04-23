from __future__ import annotations

from app.tools.runtime.catalog import register_runtime_tool_definition


_SESSION_TOOL_DEFINITIONS = [
    register_runtime_tool_definition(
        name="session.record",
        toolset="session",
        module="app.tools.session.session_search_tool",
        summary="Record a session message.",
    ),
    register_runtime_tool_definition(
        name="session.search",
        toolset="session",
        module="app.tools.session.session_search_tool",
        summary="Search stored session history.",
    ),
]

def session_search_tool_definitions() -> list[dict[str, str]]:
    return [
        {
            "name": definition.name,
            "toolset": definition.toolset,
            "module": definition.module,
            "summary": definition.summary,
        }
        for definition in _SESSION_TOOL_DEFINITIONS
    ]
