from __future__ import annotations

from app.tools.runtime.catalog import register_runtime_tool_definition


_TODO_TOOL_DEFINITION = register_runtime_tool_definition(
    name="todo.write",
    toolset="planning",
    module="app.tools.planning.todo_tool",
    summary="Todo/planning tool slot.",
)

def todo_tool_definition() -> dict[str, str]:
    return {
        "name": _TODO_TOOL_DEFINITION.name,
        "toolset": _TODO_TOOL_DEFINITION.toolset,
        "module": _TODO_TOOL_DEFINITION.module,
        "summary": _TODO_TOOL_DEFINITION.summary,
    }
