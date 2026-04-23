from __future__ import annotations


def browser_tool_definition() -> dict[str, str]:
    """Hermes-aligned browser tool slot for future real browser imports."""

    return {
        "toolset": "browser",
        "module": "app.tools.browser.browser_tool",
        "summary": "Browser automation entry point placeholder aligned to Hermes structure.",
    }
