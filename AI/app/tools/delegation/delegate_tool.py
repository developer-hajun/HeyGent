from __future__ import annotations


def delegate_tool_definition() -> dict[str, str]:
    """Delegate tool surface separate from orchestration lifecycle code."""

    return {
        "toolset": "delegation",
        "module": "app.tools.delegation.delegate_tool",
        "summary": "Parent-to-child delegation tool surface placeholder.",
    }
