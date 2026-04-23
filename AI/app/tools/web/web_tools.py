from __future__ import annotations


def web_tool_definitions() -> list[dict[str, str]]:
    return [
        {"name": "web_search", "toolset": "web"},
        {"name": "web_extract", "toolset": "web"},
    ]
