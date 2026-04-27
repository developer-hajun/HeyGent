from __future__ import annotations


def browser_tool_definition() -> dict[str, str]:
    """나중에 실제 브라우저 자동화 구현을 연결할 자리다."""

    return {
        "toolset": "browser",
        "module": "app.tools.browser.browser_tool",
        "summary": "Browser automation entry point placeholder.",
    }
