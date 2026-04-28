from __future__ import annotations

from app.tools.runtime.catalog import register_runtime_tool_definition


TODO_SCHEMA = {
    "name": "todo",
    "description": (
        "Manage the current agent task list. Omit todos to read the current list. "
        "Provide todos to replace or merge the list. Always returns the full list."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "todos": {
                "type": "array",
                "description": "Todo items to write. Omit this field to read.",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "content": {"type": "string"},
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed", "cancelled"],
                        },
                    },
                    "required": ["id", "content", "status"],
                },
            },
            "merge": {
                "type": "boolean",
                "description": "When true, update existing items by id and append new items.",
                "default": False,
            },
        },
        "required": [],
    },
}

_TODO_TOOL_DEFINITION = register_runtime_tool_definition(
    name="todo",
    toolset="planning",
    module="app.tools.planning.todo_tool",
    summary="Read or update the current agent todo list.",
    schema=TODO_SCHEMA,
    result_format="json",
)


def todo_tool_definition() -> dict[str, object]:
    return {
        "name": _TODO_TOOL_DEFINITION.name,
        "toolset": _TODO_TOOL_DEFINITION.toolset,
        "module": _TODO_TOOL_DEFINITION.module,
        "summary": _TODO_TOOL_DEFINITION.summary,
        "schema": _TODO_TOOL_DEFINITION.schema,
        "result_format": _TODO_TOOL_DEFINITION.result_format,
    }
