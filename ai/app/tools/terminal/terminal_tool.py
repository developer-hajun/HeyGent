from __future__ import annotations

from app.tools.runtime.catalog import register_runtime_tool_definition


_TERMINAL_TOOL_DEFINITION = register_runtime_tool_definition(
    name="terminal.run",
    toolset="terminal",
    module="app.tools.terminal.terminal_tool",
    summary="Run a local terminal command. Provide either command or argv.",
    schema={
        "description": "Run a local terminal command. Use command for shell text, or argv for an argument list. Provide at least one of command or argv.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command text to execute, for example: dir ai\\app\\tools",
                },
                "argv": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Command argument list, for example: ['python', '-c', 'print(123)']",
                },
                "cwd": {
                    "type": "string",
                    "description": "Optional working directory.",
                },
                "timeout_seconds": {
                    "type": "number",
                    "description": "Optional timeout in seconds.",
                },
            },
            "required": [],
        },
    },
)

def terminal_tool_definition() -> dict[str, str]:
    return {
        "name": _TERMINAL_TOOL_DEFINITION.name,
        "toolset": _TERMINAL_TOOL_DEFINITION.toolset,
        "module": _TERMINAL_TOOL_DEFINITION.module,
        "summary": _TERMINAL_TOOL_DEFINITION.summary,
    }
