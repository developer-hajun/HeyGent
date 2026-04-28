from __future__ import annotations

from app.tools.runtime.catalog import register_runtime_tool_definition


_SKILLS_TOOL_DEFINITIONS = [
    register_runtime_tool_definition(
        name="skills.list",
        toolset="skills",
        module="app.tools.skills.skills_tool",
        summary="List available skills.",
    ),
    register_runtime_tool_definition(
        name="skills.read",
        toolset="skills",
        module="app.tools.skills.skills_tool",
        summary="Read a specific skill document.",
    ),
]

def skills_tool_definitions() -> list[dict[str, str]]:
    return [
        {
            "name": definition.name,
            "toolset": definition.toolset,
            "module": definition.module,
            "summary": definition.summary,
        }
        for definition in _SKILLS_TOOL_DEFINITIONS
    ]
