from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.tools.runtime.catalog import RuntimeToolDefinition, list_registered_runtime_tool_definitions


@dataclass(frozen=True, slots=True)
class RuntimeToolEntry:
    definition: RuntimeToolDefinition
    handler: Callable


def discover_runtime_tool_definitions() -> list[RuntimeToolDefinition]:
    _discover_runtime_tool_modules()
    return list_registered_runtime_tool_definitions()


def build_runtime_tool_entries(handler_by_name: dict[str, Callable]) -> dict[str, RuntimeToolEntry]:
    entries: dict[str, RuntimeToolEntry] = {}
    for definition in discover_runtime_tool_definitions():
        if not definition.enabled:
            continue
        handler = handler_by_name.get(definition.name)
        if handler is None:
            continue
        entries[definition.name] = RuntimeToolEntry(definition=definition, handler=handler)
    return entries


def list_runtime_tool_definitions(handler_by_name: dict[str, Callable]) -> list[dict[str, Any]]:
    entries = build_runtime_tool_entries(handler_by_name)
    return [
        {
            "name": entry.definition.name,
            "toolset": entry.definition.toolset,
            "summary": entry.definition.summary,
            "module": entry.definition.module,
            "schema": entry.definition.schema,
            "result_format": entry.definition.result_format,
        }
        for _, entry in sorted(entries.items())
    ]


def list_runtime_tool_schemas(handler_by_name: dict[str, Callable]) -> list[dict[str, Any]]:
    entries = build_runtime_tool_entries(handler_by_name)
    return [
        {"type": "function", "function": entry.definition.schema}
        for _, entry in sorted(entries.items())
    ]


def _discover_runtime_tool_modules() -> None:
    from app.tools.file import file_tools  # noqa: F401
    from app.tools.planning import step_tool  # noqa: F401
    from app.tools.planning import todo_tool  # noqa: F401
    from app.tools.session import session_search_tool  # noqa: F401
    from app.tools.skills import skills_tool  # noqa: F401
    from app.tools.terminal import terminal_tool  # noqa: F401
