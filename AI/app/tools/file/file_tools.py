from __future__ import annotations


def file_tool_definitions() -> list[dict[str, str]]:
    """Hermes-style file tool slots that can later host copied implementations."""

    return [
        {"name": "read_file", "toolset": "file"},
        {"name": "write_file", "toolset": "file"},
        {"name": "patch", "toolset": "file"},
        {"name": "search_files", "toolset": "file"},
    ]
