from __future__ import annotations


def send_message_tool_definition() -> dict[str, str]:
    return {
        "toolset": "messaging",
        "module": "app.tools.messaging.send_message_tool",
        "summary": "Outbound messaging tool slot.",
    }
