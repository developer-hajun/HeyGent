from __future__ import annotations


def file_tool_definitions() -> list[dict[str, str]]:
    """나중에 실제 파일 도구 구현을 연결할 자리다."""

    return [
        {"name": "read_file", "toolset": "file"},
        {"name": "write_file", "toolset": "file"},
        {"name": "patch", "toolset": "file"},
        {"name": "search_files", "toolset": "file"},
    ]
